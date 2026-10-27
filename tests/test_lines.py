import json
import struct

from lab import lines as L


def test_added_lines_counts_only_new():
    assert L.added_lines("a\nb\nc", "a\nb\nc") == 0
    assert L.added_lines("a\nc", "a\nb\nc") == 1
    assert L.added_lines("", "x\ny\nz") == 3
    assert L.added_lines("a\nb\nc", "a") == 0  # pure deletion adds nothing


def test_count_plus_ignores_context_and_minus():
    hunks = [{"lines": ["+new1", "-gone", " ctx", "+new2"]}]
    assert L.count_plus(hunks) == 2


def test_counted_skips_lockfiles_and_blobs():
    assert L.counted("src/app.py")
    assert not L.counted("uv.lock")
    assert not L.counted("dist/app.min.js")
    assert not L.counted("findings/survey.csv")


def test_tally_offsets_and_skips():
    t = L.Tally()
    t.add("claude", "/r/a.py", 10)
    t.add("antigravity", "/r/a.py", 5)
    t.add("claude", "/r/uv.lock", 99)  # skipped
    t.add("claude", "", 3)             # no path, skipped
    assert t.total == 15
    assert t.by_source["claude"] == 10
    assert t.by_file[L.__dict__["os"].path.realpath("/r/a.py")] == 15


def test_claude_create_counts_full_content():
    entry = {"timestamp": "2026-10-25T00:00:00Z",
             "toolUseResult": {"type": "create", "filePath": "/r/new.py", "content": "a\nb\nc\n"}}
    assert L.claude_entry_lines(entry) == [("/r/new.py", 3)]


def test_claude_edit_counts_plus_lines():
    entry = {"toolUseResult": {"filePath": "/r/x.py",
             "structuredPatch": [{"lines": ["+one", " ctx", "+two", "-old"]}]}}
    assert L.claude_entry_lines(entry) == [("/r/x.py", 2)]


def test_claude_bash_heredoc_diff():
    entry = {"toolUseResult": {"bashEditDiff": {"files": [
        {"filePath": "/r/y.sh", "hunks": [{"lines": ["+a", "+b"]}]}]}}}
    assert L.claude_entry_lines(entry) == [("/r/y.sh", 2)]


def test_claude_non_edit_result_ignored():
    assert L.claude_entry_lines({"toolUseResult": {"stdout": "hi"}}) == []
    assert L.claude_entry_lines({"toolUseResult": "string result"}) == []


def test_agy_call_lines_per_tool():
    assert L.agy_call_lines("write_to_file", {"TargetFile": "/f", "CodeContent": "a\nb"}) == ("/f", 2)
    assert L.agy_call_lines("write_file", {"Path": "/f", "Content": "a\nb\nc"}) == ("/f", 3)
    assert L.agy_call_lines("replace_file_content",
                            {"TargetFile": "/f", "TargetContent": "a", "ReplacementContent": "a\nb\nc"}) == ("/f", 2)
    assert L.agy_call_lines("edit_file",
                            {"Path": "/f", "Target": "x", "Replacement": "x\ny"}) == ("/f", 1)
    assert L.agy_call_lines("unknown_tool", {}) is None


def test_agy_multi_replace_sums_chunks():
    chunks = [{"TargetContent": "a", "ReplacementContent": "a\nb"},
              {"TargetContent": "", "ReplacementContent": "x\ny\nz"}]
    assert L.agy_call_lines("multi_replace_file_content",
                            {"TargetFile": "/f", "ReplacementChunks": chunks}) == ("/f", 4)


def _tag(field, wire):
    return (field << 3) | wire


def _ld(field, data):
    return bytes([_tag(field, 2)]) + bytes([len(data)]) + data


def _varint_field(field, value):
    out = bytearray([_tag(field, 0)])
    while True:
        b = value & 0x7F
        value >>= 7
        out.append(b | (0x80 if value else 0))
        if not value:
            return bytes(out)


def test_pb_reader_roundtrip_nested():
    # build message: field5 { field1 { field1: <ts> }  field4 { field2: name, field3: argsjson } }
    inner_ts = _varint_field(1, 1792826910)
    f5_1 = _ld(1, inner_ts)
    args = json.dumps({"Path": "/f", "Content": "a\nb\nc"}).encode()
    f5_4 = _ld(4, _ld(2, b"write_file") + _ld(3, args))
    payload = _ld(5, f5_1 + f5_4)
    assert L.pb_get(payload, 5, 1, 1) == 1792826910
    assert L.pb_get(payload, 5, 4, 2) == b"write_file"
    assert json.loads(L.pb_get(payload, 5, 4, 3))["Content"] == "a\nb\nc"


def test_pb_get_missing_field_returns_none():
    assert L.pb_get(_ld(5, _varint_field(1, 7)), 5, 9, 9) is None


def test_parse_numstat_handles_rename_and_binary(tmp_path):
    text = "10\t2\tsrc/a.py\n-\t-\timg.png\n3\t0\told.py => new.py\n5\t1\tuv.lock\n"
    out = L.parse_numstat(text, tmp_path)
    assert out[L.os.path.realpath(tmp_path / "src/a.py")] == 10
    assert out[L.os.path.realpath(tmp_path / "new.py")] == 3
    assert all("img.png" not in k and "uv.lock" not in k for k in out)

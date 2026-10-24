from drama_pipeline.stage7_emit import public_work


def test_public_work_drops_the_tlg_source_header():
    work = {
        "id": "agamemnon",
        "title": "Agamemnon",
        "expected_sourcedesc": 'Aeschylus Trag. (c. 6-5 B.C.), Agamemnon (0085: 005) "..."',
    }
    out = public_work(work)
    assert "expected_sourcedesc" not in out
    assert out == {"id": "agamemnon", "title": "Agamemnon"}
    assert "expected_sourcedesc" in work  # the input is not mutated

"""Shops mischen (shops.mix): ein großer Shop verdrängt die anderen nicht."""

from backend import shops


def item(shop, score, n):
    return {"id": f"{shop}-{n}", "shop": shop, "score": score}


def test_equal_scores_take_turns():
    ranked = [item("AliExpress", 0, n) for n in range(4)] + [item("Unipolar", 0, 0), item("Converse", 0, 0)]
    assert [i["shop"] for i in shops.mix(ranked)[:3]] == ["AliExpress", "Unipolar", "Converse"]


def test_best_match_stays_first_and_nothing_is_lost():
    ranked = [item("Big", 10, n) for n in range(5)] + [item("Small", 3, 0)]
    mixed = shops.mix(ranked)
    assert mixed[0]["id"] == "Big-0" and len(mixed) == 6
    assert mixed.index(ranked[-1]) == 5                      # 3 Punkte bleiben hinter 10*0.9^4


def test_one_shop_unchanged():
    ranked = [item("Solo", 5 - n, n) for n in range(3)]
    assert shops.mix(ranked) == ranked

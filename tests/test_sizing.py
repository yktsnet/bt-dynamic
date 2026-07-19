import pytest

from bt_dynamic.sizing import apply_lot_strategy, lot_table


def _trade(regime, ax1, pips):
    return {"regime": regime, "ax1": ax1, "result_pips": pips}


TRADES = [
    _trade((0, 0), 10.0, 5.0),
    _trade((1, 0), 20.0, -3.0),
    _trade((2, 1), 30.0, 8.0),
]


def test_lot_table_normalized_to_mean_one():
    lots = lot_table(TRADES)
    for method in ("flat", "proportional", "inverse"):
        assert lots[method].mean() == pytest.approx(1.0)


def test_lot_table_orderings():
    lots = lot_table(TRADES)
    # proportional grows with ax1, inverse shrinks
    assert lots["proportional"].iloc[2] > lots["proportional"].iloc[0]
    assert lots["inverse"].iloc[2] < lots["inverse"].iloc[0]
    assert (lots["flat"] == 1.0).all()


def test_apply_lot_strategy_sizes_pips():
    strategy = {(0, 0): "flat", (1, 0): "proportional", (2, 1): "inverse"}
    sized = apply_lot_strategy(TRADES, strategy)

    lots = lot_table(TRADES)
    assert sized[0]["lot"] == pytest.approx(1.0)
    assert sized[1]["sized_pips"] == pytest.approx(
        -3.0 * lots["proportional"].iloc[1]
    )
    assert sized[2]["sized_pips"] == pytest.approx(8.0 * lots["inverse"].iloc[2])
    # original trades untouched
    assert "lot" not in TRADES[0]


def test_apply_lot_strategy_missing_cell_rejected():
    with pytest.raises(ValueError, match="missing cell"):
        apply_lot_strategy(TRADES, {(0, 0): "flat"})


def test_apply_lot_strategy_empty_trades():
    assert apply_lot_strategy([], {}) == []

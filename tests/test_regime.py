from bt_dynamic.regime import classify

THRESHOLDS = {
    "ax1_weak": 20.0,
    "ax1_strong": 25.0,
    "vol_lo": 0.8,
    "vol_hi": 1.2,
    "direction_band": 5.0,
}


def test_classify_all_levels():
    # weak trend, low vol (0.01/0.02 = 0.5), neutral direction
    assert classify(10.0, 0.01, 0.02, 50.0, **THRESHOLDS) == (0, 0, None)
    # mid trend, normal vol (ratio 1.0), bullish direction
    assert classify(22.0, 0.02, 0.02, 60.0, **THRESHOLDS) == (1, 1, "BUY")
    # strong trend, high vol (ratio 1.5), bearish direction
    assert classify(30.0, 0.03, 0.02, 40.0, **THRESHOLDS) == (2, 2, "SELL")


def test_classify_band_edges():
    # exactly on the neutral band edge stays neutral
    assert classify(10.0, 0.02, 0.02, 55.0, **THRESHOLDS)[2] is None
    assert classify(10.0, 0.02, 0.02, 45.0, **THRESHOLDS)[2] is None
    # zero mean falls back to ratio 1.0 (class 1)
    assert classify(10.0, 0.02, 0.0, 50.0, **THRESHOLDS)[1] == 1


def test_classify_injected_thresholds():
    # ax1=22 is class 1 with weak=20 but class 0 with weak=23
    overridden = {**THRESHOLDS, "ax1_weak": 23.0}
    assert classify(22.0, 0.02, 0.02, 50.0, **overridden)[0] == 0

    # ratio 1.3 is class 2 with hi=1.2 but class 1 with hi=1.4
    overridden = {**THRESHOLDS, "vol_hi": 1.4}
    assert classify(22.0, 0.026, 0.02, 50.0, **overridden)[1] == 1


def test_classify_custom_direction_center():
    # a direction oscillator centered on 0 instead of 50
    result = classify(
        30.0, 0.02, 0.02, 3.0, **THRESHOLDS, direction_center=0.0
    )
    assert result[2] is None  # 3.0 inside [-5, +5]
    result = classify(
        30.0, 0.02, 0.02, 8.0, **THRESHOLDS, direction_center=0.0
    )
    assert result[2] == "BUY"

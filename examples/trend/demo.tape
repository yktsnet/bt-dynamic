# VHS demo: bt-dynamic
# 生成: リポルートで `nix-shell -p vhs jq "python3.withPackages(ps: with ps; [pandas numpy])" --run 'vhs examples/trend/demo.tape'`
# 示したいこと: セル対応表はJSONで外部注入され、その割り当て（"2,1": follow 等）が
#               そのままエントリー判定（regime=(2,1) follow）を決める
# 尺規範: 10秒前後（成績サマリーは映さない — 合成データの数字を実績と誤読させない）

Output examples/trend/demo.gif

Set FontSize 18
Set Width 1000
Set Height 600
Set Theme "Catppuccin Mocha"
Set TypingSpeed 20ms

Hide
Type "cd examples/trend; d=data/sample_m5.jsonl"
Enter
Type `bt-dynamic() { PYTHONPATH=../../src python -m bt_dynamic.cli --start 2025-01-09 --days 1 "$@" | head -5; }`
Enter
Type "clear"
Enter
Show

Type "# セル対応表はJSONで注入する — エンジンは戦略を持たない"
Enter
Sleep 500ms

Type "jq .regime_strategy config.json"
Enter
Sleep 2200ms

Type@12ms "bt-dynamic --config config.json --data $d"
Enter
Sleep 5000ms

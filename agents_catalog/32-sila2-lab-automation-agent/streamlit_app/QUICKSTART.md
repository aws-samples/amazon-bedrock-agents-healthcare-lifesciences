# Phase 7 Demo - Quick Start

## 前提条件

1. **ポートフォワード起動**
```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent
./start_port_forward.sh
```

別ターミナルで実行し、起動したままにしてください。

2. **UI起動**
```bash
cd streamlit_app
./run_demo.sh
```

3. **ブラウザアクセス**
```
http://localhost:8501
```

## デモ手順 (4分)

### 正常系 (0:00-2:00)

1. **温度設定** (0:00)
   - Target: 35°C
   - 「🔥 Set Temperature」クリック

2. **AI分析** (1:00)
   - 「🤖 Trigger AI Analysis」クリック
   - 期待: "順調に上昇中" (5°C/min)

3. **目標到達** (2:00)
   - Event Logに「目標温度到達」表示

### 異常系 (2:30-4:00)

4. **シナリオ切替** (2:30)
   - 「🔄 Toggle Scenario」クリック

5. **AI分析** (3:30)
   - 「🤖 Trigger AI Analysis」クリック
   - 期待: "異常検知 - 上昇率が遅い" (2°C/min)

## トラブルシューティング

### Bridge offline表示
```bash
# ポートフォワード確認
ps aux | grep ssm
# 再起動
./start_port_forward.sh
```

### Lambda呼び出しエラー
```bash
aws sts get-caller-identity
```

# フォルダ構成最適化計画

## 目的
プロジェクトを公開可能な構造に整理し、ユーザーが理解しやすくする。

## 現在の構成

```
32-sila2-lab-automation-agent/
├── .bedrock_agentcore/
├── agentcore/
├── bridge_container/
├── infrastructure/
├── lambda/
├── mock_devices/
├── proto/
├── scripts/
├── streamlit_app/
├── README.md
├── requirements.txt
└── [各種計画ファイル].md
```

## 最適化後の構成

```
32-sila2-lab-automation-agent/
├── README.md                          # メインドキュメント
├── requirements.txt                   # Python依存関係
├── .gitignore
├── .bedrock_agentcore.yaml           # AgentCore設定
│
├── docs/                              # ドキュメント集約
│   ├── deployment.md                 # デプロイ手順
│   ├── architecture.md               # アーキテクチャ説明
│   ├── development.md                # 開発者向けガイド
│   └── troubleshooting.md            # トラブルシューティング
│
├── src/                               # ソースコード
│   ├── bridge/                       # bridge_container → 移動
│   │   ├── bridge_server.py
│   │   ├── Dockerfile
│   │   └── proto/
│   ├── devices/                      # mock_devices → 移動
│   │   ├── mock_server.py
│   │   ├── Dockerfile
│   │   └── proto/
│   ├── lambda/                       # lambda/ → 移動
│   │   ├── invoker/
│   │   └── tools/
│   └── proto/                        # proto/ → 移動（共通定義）
│       ├── sila2_basic.proto
│       ├── sila2_streaming.proto
│       └── sila2_tasks.proto
│
├── agentcore/                         # AgentCore設定（そのまま）
│   ├── agent_instructions.txt
│   ├── gateway_config.py
│   ├── runtime_config.py
│   └── verify_setup.py
│
├── infrastructure/                    # CloudFormation（整理）
│   ├── main.yaml                     # （将来）メインテンプレート
│   ├── bridge_container_ecs.yaml     # 名前変更
│   ├── lambda_proxy.yaml
│   ├── events_sns.yaml               # phase6-cfn.yaml → 名前変更済み
│   └── legacy/                       # （将来）旧テンプレート移動先
│
├── scripts/                           # デプロイスクリプト（整理）
│   ├── deploy.sh                     # メインデプロイスクリプト
│   ├── cleanup.sh                    # クリーンアップ
│   ├── test_events.sh                # テスト
│   └── utils/                        # （将来）共通関数
│
├── streamlit_app/                     # UIアプリ（そのまま）
│   ├── app.py                        # phase7_final.py → 名前変更済み
│   ├── Dockerfile
│   ├── requirements.txt
│   └── QUICKSTART.md
│
└── .bedrock_agentcore/                # AgentCore内部（そのまま）
    └── sila2_agent/                  # sila2_phase3_agent → 名前変更済み
```

## 移動・変更の詳細

### 1. ドキュメント整理

#### 新規作成: `docs/deployment.md`
```markdown
# デプロイ手順

README.mdから詳細手順を移動
- 前提条件
- ステップバイステップ手順
- トラブルシューティング
```

#### 新規作成: `docs/architecture.md`
```markdown
# アーキテクチャ

システム構成図と説明
- コンポーネント図
- データフロー
- AWS サービス構成
```

#### 新規作成: `docs/development.md`
```markdown
# 開発者ガイド

開発環境セットアップ
- ローカル開発
- テスト方法
- コントリビューション
```

#### 既存ファイルの移動
```bash
# 計画ファイルをdocs/に移動（参考資料として）
mv DEPLOYMENT_OPTIMIZATION_PLAN.md docs/future_optimization.md
mv NAMING_REFACTORING_PLAN.md docs/naming_refactoring.md
mv FOLDER_STRUCTURE_PLAN.md docs/folder_structure.md

# 不要な計画ファイルは削除
rm CLEANUP_PLAN.md
rm MOVE_PLAN.md
rm REQUIRED_FILES.md
```

### 2. ソースコード整理

```bash
# src/ ディレクトリ作成
mkdir -p src

# bridge_container → src/bridge
mv bridge_container src/bridge

# mock_devices → src/devices
mv mock_devices src/devices

# lambda → src/lambda
mv lambda src/lambda

# proto → src/proto
mv proto src/proto
```

### 3. インフラストラクチャ整理

```bash
# ファイル名変更（より明確に）
mv infrastructure/bridge_container_ecs_no_alb.yaml infrastructure/bridge_container_ecs.yaml

# 将来のlegacyフォルダ準備（今は作成のみ）
mkdir -p infrastructure/legacy
```

### 4. スクリプト整理

```bash
# メインデプロイスクリプト作成（既存スクリプトを統合）
# 詳細はDEPLOYMENT_OPTIMIZATION_PLANを参照

# utilsフォルダ準備（将来用）
mkdir -p scripts/utils
```

## パス参照の更新

### 更新が必要なファイル

#### 1. `agentcore/runtime_config.py`
```python
# 変更前
dockerfile_path = "../bridge_container/Dockerfile"

# 変更後
dockerfile_path = "../src/bridge/Dockerfile"
```

#### 2. `infrastructure/bridge_container_ecs.yaml`
```yaml
# 変更前
# bridge_container への参照

# 変更後
# src/bridge への参照
```

#### 3. `scripts/` 内の各スクリプト
```bash
# 変更前
cd bridge_container

# 変更後
cd src/bridge
```

#### 4. `README.md`
```markdown
# 変更前
詳細は `bridge_container/` を参照

# 変更後
詳細は `src/bridge/` を参照
```

#### 5. `.bedrock_agentcore.yaml`
```yaml
# 変更前
dockerfile: bridge_container/Dockerfile

# 変更後
dockerfile: src/bridge/Dockerfile
```

## 実行手順

### Phase 1: ドキュメント整理（30分）
```bash
# 1. docs/ ディレクトリ作成
mkdir -p docs

# 2. 新規ドキュメント作成
touch docs/deployment.md
touch docs/architecture.md
touch docs/development.md
touch docs/troubleshooting.md

# 3. 既存計画ファイル移動
mv DEPLOYMENT_OPTIMIZATION_PLAN.md docs/future_optimization.md
mv NAMING_REFACTORING_PLAN.md docs/naming_refactoring.md

# 4. 不要ファイル削除
rm CLEANUP_PLAN.md MOVE_PLAN.md REQUIRED_FILES.md
```

### Phase 2: ソースコード移動（20分）
```bash
# 1. src/ ディレクトリ作成
mkdir -p src

# 2. ディレクトリ移動（git mvを使用）
git mv bridge_container src/bridge
git mv mock_devices src/devices
git mv lambda src/lambda
git mv proto src/proto
```

### Phase 3: パス参照更新（40分）
```bash
# 1. 全ファイルで"bridge_container"を検索
grep -r "bridge_container" --include="*.py" --include="*.yaml" --include="*.sh" --include="*.md" .

# 2. 各ファイルを手動で更新
# - agentcore/runtime_config.py
# - infrastructure/*.yaml
# - scripts/*.sh
# - README.md
# - .bedrock_agentcore.yaml

# 3. 同様に"mock_devices", "lambda/", "proto/"も検索・更新
```

### Phase 4: インフラ整理（10分）
```bash
# ファイル名変更
git mv infrastructure/bridge_container_ecs_no_alb.yaml infrastructure/bridge_container_ecs.yaml

# legacyフォルダ作成（将来用）
mkdir -p infrastructure/legacy
```

### Phase 5: 動作確認（30分）
```bash
# 1. パス参照が正しいか確認
python -m py_compile agentcore/runtime_config.py

# 2. CloudFormationテンプレート検証
aws cloudformation validate-template --template-body file://infrastructure/bridge_container_ecs.yaml

# 3. デプロイテスト（可能であれば）
```

## チェックリスト

### ドキュメント
- [ ] `docs/` ディレクトリ作成
- [ ] 新規ドキュメント作成（4ファイル）
- [ ] 計画ファイル移動
- [ ] 不要ファイル削除

### ソースコード
- [ ] `src/` ディレクトリ作成
- [ ] `bridge_container` → `src/bridge` 移動
- [ ] `mock_devices` → `src/devices` 移動
- [ ] `lambda` → `src/lambda` 移動
- [ ] `proto` → `src/proto` 移動

### パス参照更新
- [ ] `agentcore/runtime_config.py`
- [ ] `infrastructure/*.yaml`
- [ ] `scripts/*.sh`
- [ ] `README.md`
- [ ] `.bedrock_agentcore.yaml`
- [ ] `streamlit_app/` 内のファイル

### インフラ
- [ ] `bridge_container_ecs_no_alb.yaml` → `bridge_container_ecs.yaml`
- [ ] `infrastructure/legacy/` 作成

### 動作確認
- [ ] Python構文チェック
- [ ] CloudFormationテンプレート検証
- [ ] デプロイテスト

## 注意事項

1. **Git履歴**: `git mv` を使用してファイル履歴を保持
2. **バックアップ**: 変更前にブランチ作成を推奨
3. **段階的実行**: Phase 1-5を順番に実行
4. **テスト**: 各Phaseの後に動作確認
5. **ドキュメント**: README.mdを最後に更新

## 所要時間

- Phase 1 (ドキュメント): 30分
- Phase 2 (ソースコード移動): 20分
- Phase 3 (パス参照更新): 40分
- Phase 4 (インフラ整理): 10分
- Phase 5 (動作確認): 30分
- **合計: 約2時間30分**

## 次のステップ

1. この計画を確認・承認
2. 命名修正計画（NAMING_REFACTORING_PLAN.md）を先に実行
3. このフォルダ構成計画を実行
4. デプロイ最適化（DEPLOYMENT_OPTIMIZATION_PLAN.md）は公開後に実施

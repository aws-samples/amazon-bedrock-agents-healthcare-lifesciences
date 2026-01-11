# 命名修正の安全な実施ガイド

## 🎯 実施方針

**段階的アプローチ**: 一度に全て変更せず、検証しながら進める

## 📋 実施手順

### Phase 0: 準備（5分）

**現在の状況**:
- ✅ ブランチ: `sila2-agent-phase3-development` (作業中)
- ⚠️ 未コミットの変更: `.bedrock_agentcore.yaml`
- ⚠️ 未追跡ファイル: 複数の計画ファイルとStreamlitファイル

```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog

# 1. フォルダ全体のバックアップ作成（最優先）
BACKUP_NAME="32-sila2-lab-automation-agent-backup-$(date +%Y%m%d-%H%M%S)"
cp -r 32-sila2-lab-automation-agent "$BACKUP_NAME"
echo "✓ Backup created: $BACKUP_NAME"

# 作業ディレクトリに移動
cd 32-sila2-lab-automation-agent

# 2. 現在の状態を確認（既に実行済み）
git status

# 3. 作業ブランチは既に存在（sila2-agent-phase3-development）
# 新しいブランチは不要

# 4. バックアップタグ作成（念のため）
git tag backup-before-refactor-$(date +%Y%m%d-%H%M%S)

# 5. 変更前のファイル一覧を記録
find . -type f \( -name "*.py" -o -name "*.yaml" -o -name "*.sh" \) > /tmp/files_before.txt

# 6. 未コミットの変更を一時保存（オプション）
# git stash push -m "WIP: before refactoring"
```

### Phase 1: ファイル名変更のみ（5分）

```bash
# ファイル名だけ変更（内容は変更しない）
git mv main_agentcore_phase3.py main_agentcore.py
git mv .bedrock_agentcore/sila2_phase3_agent .bedrock_agentcore/sila2_agent
git mv infrastructure/phase6-cfn.yaml infrastructure/events_sns.yaml
git mv scripts/test-phase6.sh scripts/test_events.sh
git mv streamlit_app/phase7_final.py streamlit_app/app.py
git mv test_phase4_integration.py test_integration.py
git mv docs/architecture_phase4.md docs/architecture.md

# コミット
git add -A
git commit -m "refactor: rename files to remove phase naming"

# 確認
git log -1 --stat
```

**✅ チェックポイント**: ファイルが正しくリネームされたか確認

### Phase 2: 設定ファイルの参照更新（10分）

```bash
# .bedrock_agentcore.yaml
sed -i 's/sila2_phase3_agent/sila2_agent/g' .bedrock_agentcore.yaml
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' .bedrock_agentcore.yaml
sed -i 's/sila2_phase7_memory/sila2_memory/g' .bedrock_agentcore.yaml

# 確認
git diff .bedrock_agentcore.yaml

# 問題なければコミット
git add .bedrock_agentcore.yaml
git commit -m "refactor: update AgentCore config references"
```

**✅ チェックポイント**: YAMLファイルが壊れていないか確認
```bash
python3 -c "import yaml; yaml.safe_load(open('.bedrock_agentcore.yaml'))"
```

### Phase 3: Pythonコードの参照更新（10分）

```bash
# Lambda関数名変更
sed -i 's/phase7-analyze_heating_rate/sila2-analyze-heating-rate/g' agentcore/gateway_config.py
sed -i 's/phase7-execute_autonomous_control/sila2-execute-autonomous-control/g' agentcore/gateway_config.py
sed -i 's/phase7-analyze_heating_rate/sila2-analyze-heating-rate/g' agentcore/verify_setup.py
sed -i 's/phase7-execute_autonomous_control/sila2-execute-autonomous-control/g' agentcore/verify_setup.py

# 構文チェック
python3 -m py_compile agentcore/gateway_config.py
python3 -m py_compile agentcore/verify_setup.py

# 問題なければコミット
git add agentcore/
git commit -m "refactor: update Lambda function names in Python code"
```

**✅ チェックポイント**: Pythonファイルが構文エラーなく実行できるか

### Phase 4: スクリプトの参照更新（10分）

```bash
# scripts/00
sed -i 's/sila2-phase6-stack/sila2-events-stack/g' scripts/00_setup_vpc_endpoint.sh

# scripts/03
sed -i 's/phase6-cfn\.yaml/events_sns.yaml/g' scripts/03_deploy_ecs.sh
sed -i 's/sila2-phase6-stack/sila2-events-stack/g' scripts/03_deploy_ecs.sh
sed -i 's/phase6-lambda\.zip/events-lambda.zip/g' scripts/03_deploy_ecs.sh

# scripts/06
sed -i 's/sila2_phase3_agent/sila2_agent/g' scripts/06_deploy_agentcore.sh
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' scripts/06_deploy_agentcore.sh
sed -i 's/sila2_phase7_memory/sila2_memory/g' scripts/06_deploy_agentcore.sh
sed -i 's/sila2-phase6-stack-LambdaExecutionRole/sila2-events-stack-LambdaExecutionRole/g' scripts/06_deploy_agentcore.sh

# scripts/07
sed -i 's/test_phase4_integration\.py/test_integration.py/g' scripts/07_run_tests.sh

# 構文チェック（bashスクリプト）
bash -n scripts/00_setup_vpc_endpoint.sh
bash -n scripts/03_deploy_ecs.sh
bash -n scripts/06_deploy_agentcore.sh
bash -n scripts/07_run_tests.sh

# コミット
git add scripts/
git commit -m "refactor: update references in deployment scripts"
```

**✅ チェックポイント**: スクリプトが構文エラーなく実行できるか

### Phase 5: ドキュメント・その他の更新（10分）

```bash
# README.md
sed -i 's/phase7_app\.py/app.py/g' README.md
sed -i 's/phase7_final\.py/app.py/g' README.md
sed -i 's/phase6-invoker/sila2-agentcore-invoker/g' README.md

# streamlit_app/
sed -i 's/phase7_final\.py/app.py/g' streamlit_app/QUICKSTART.md
sed -i 's/Phase 7 Final Implementation/SiLA2 Lab Automation Streamlit UI/g' streamlit_app/app.py

# scripts/test_events.sh
sed -i 's/Testing Phase 6 deployment/Testing SNS and EventBridge integration/g' scripts/test_events.sh

# infrastructure/
sed -i 's/Phase 6 - EventBridge/EventBridge/g' infrastructure/events_sns.yaml
sed -i 's/Security group for Phase 6 Lambda function/Security group for Lambda function/g' infrastructure/events_sns.yaml
sed -i 's/phase6-cfn\.yaml/events_sns.yaml/g' infrastructure/eventbridge-scheduler.yaml

# その他
sed -i 's/08_integrate_phase3\.sh/08_integrate_agentcore.sh/g' scripts/README.md
sed -i 's/main_agentcore_phase3\.py/main_agentcore.py/g' REQUIRED_FILES.md
sed -i 's/streamlit_app\/phase7_final\.py/streamlit_app\/app.py/g' REQUIRED_FILES.md

# CloudFormation検証
aws cloudformation validate-template --template-body file://infrastructure/events_sns.yaml

# コミット
git add .
git commit -m "refactor: update documentation and descriptions"
```

**✅ チェックポイント**: CloudFormationテンプレートが有効か確認

### Phase 6: 最終検証（10分）

```bash
# 1. "phase"残存確認
echo "=== Checking for remaining 'phase' references ==="
grep -r "phase" --include="*.py" --include="*.yaml" --include="*.sh" . \
  --exclude-dir=".git" \
  | grep -v "PLAN.md" \
  | grep -v "CLEANUP_PLAN.md" \
  | grep -v "SAFE_EXECUTION_GUIDE.md" \
  | grep -v "NAMING_REFACTORING_COMPLETE_PLAN.md" \
  | grep -v "docs/" \
  | grep -v "eventbridge-scheduler.yaml"

# 2. 全Pythonファイルの構文チェック
echo "=== Python syntax check ==="
find . -name "*.py" -not -path "./.git/*" -not -path "./docs/*" | while read f; do
    python3 -m py_compile "$f" && echo "✓ $f" || echo "✗ $f"
done

# 3. 全Bashスクリプトの構文チェック
echo "=== Bash syntax check ==="
find scripts -name "*.sh" | while read f; do
    bash -n "$f" && echo "✓ $f" || echo "✗ $f"
done

# 4. 変更ファイル一覧
echo "=== Changed files ==="
git diff --name-only backup-before-refactor-*

# 5. 変更内容のサマリー
echo "=== Change summary ==="
git diff --stat backup-before-refactor-*
```

### Phase 7: マージ準備（5分）

```bash
# 全ての変更を確認
git log backup-before-refactor-*..HEAD --oneline

# 問題なければmainブランチにマージ準備
git checkout main
git merge --no-ff sila2-agent-phase3-development -m "refactor: remove phase naming conventions

- Renamed 7 files to remove phase numbers
- Updated all references in code, scripts, and configs
- Updated CloudFormation templates and documentation
- All syntax checks passed"

# タグ作成
git tag refactor-complete-$(date +%Y%m%d)
```

## 🔄 ロールバック手順

問題が発生した場合：

### 方法1: フォルダバックアップから復元（最も安全）

```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog

# 現在のフォルダを削除
rm -rf 32-sila2-lab-automation-agent

# バックアップから復元（最新のバックアップを使用）
cp -r 32-sila2-lab-automation-agent-backup-YYYYMMDD-HHMMSS 32-sila2-lab-automation-agent

echo "✓ Restored from backup"
```

### 方法2: Gitで特定のPhaseまで戻る

```bash
cd /home/tetsutm/dev/amazon-bedrock-agents-healthcare-lifesciences/agents_catalog/32-sila2-lab-automation-agent

# 特定のPhaseまで戻る
git log --oneline  # コミットIDを確認
git reset --hard <commit-id>

# または完全にロールバック
git reset --hard backup-before-refactor-YYYYMMDD-HHMMSS

# 未コミットの変更を破棄
git restore .
git clean -fd
```

## ⚠️ 重要な注意事項

1. **フォルダバックアップ**: Phase 0でフォルダ全体をバックアップ（最も安全な復元方法）
2. **現在のブランチ**: `sila2-agent-phase3-development` で作業中
3. **未コミットの変更**: `.bedrock_agentcore.yaml` に変更あり（必要に応じてstashまたはコミット）
4. **AWS環境は削除済み**: 新規デプロイなので後方互換性の心配なし
5. **各Phaseでコミット**: 問題があれば該当Phaseまで戻れる
6. **検証を必ず実行**: 次のPhaseに進む前に必ずチェックポイントを確認
7. **バックアップタグ**: Phase 0で作成したGitタグに戻れる

## 📊 進捗トラッキング

- [x] Phase 0: 準備完了（フォルダバックアップ + Gitタグ）
  - ✅ バックアップ: `32-sila2-lab-automation-agent-backup-20260111-065736`
  - ✅ Gitタグ: `backup-before-refactor-20260111-065834`
  - ✅ ファイル一覧記録: 68ファイル
- [x] Phase 1: ファイル名変更完了
  - ✅ コミットID: `24e0c81`
  - ✅ リネーム: 7ファイル（main_agentcore.py, sila2_agent/, events_sns.yaml, test_events.sh, app.py, test_integration.py, architecture.md）
  - ✅ 23ファイル変更、2693行追加
- [x] Phase 2: 設定ファイル更新完了
  - ✅ コミットID: `dee4a23`
  - ✅ 更新: .bedrock_agentcore.yaml（sila2_phase3_agent→sila2_agent, main_agentcore_phase3.py→main_agentcore.py, sila2_phase7_memory→sila2_memory）
  - ✅ YAML検証: 成功
  - ✅ 1ファイル変更、11行挿入、11行削除
- [x] Phase 3: Pythonコード更新完了
  - ✅ コミットID: `f703e61`
  - ✅ 更新: agentcore/gateway_config.py, agentcore/verify_setup.py
  - ✅ Lambda関数名: phase7-analyze_heating_rate→sila2-analyze-heating-rate, phase7-execute_autonomous_control→sila2-execute-autonomous-control
  - ✅ Python構文チェック: 成功
  - ✅ 2ファイル変更、4行挿入、4行削除
- [x] Phase 4: スクリプト更新完了
  - ✅ コミットID: `f4e346d`
  - ✅ 更新: scripts/00_setup_vpc_endpoint.sh, scripts/03_deploy_ecs.sh, scripts/06_deploy_agentcore.sh, scripts/07_run_tests.sh
  - ✅ スタック名: sila2-phase6-stack→sila2-events-stack, phase6-cfn.yaml→events_sns.yaml, phase6-lambda.zip→events-lambda.zip
  - ✅ エージェント名: sila2_phase3_agent→sila2_agent, sila2_phase7_memory→sila2_memory
  - ✅ Bash構文チェック: 成功
  - ✅ 4ファイル変更、23行挿入、23行削除
- [ ] Phase 5: ドキュメント更新完了
- [ ] Phase 6: 最終検証完了
- [ ] Phase 7: マージ完了

## 🎉 完了後の確認

```bash
# 新しい名前でデプロイテスト（オプション）
# scripts/06_deploy_agentcore.sh を実行して新しい名前でデプロイできるか確認
```

## 所要時間

- **合計**: 約55分（各Phase 5-10分）
- **余裕を持って**: 1時間確保を推奨

# MySFA テストガイド

## 概要
このプロジェクトでは、Djangoのテストフレームワークを使用してコードの品質と動作を保証しています。

## テストの実行方法

### 基本的なテスト実行
```bash
# 全テストを実行
python manage.py test

# 特定のアプリのテストを実行
python manage.py test mysfa
python manage.py test accounts

# 特定のテストクラスを実行
python manage.py test mysfa.tests.MySFATestCase
python manage.py test accounts.tests.AccountsModelTest

# 特定のテストメソッドを実行
python manage.py test mysfa.tests.MySFATestCase.test_home_page_loads
```

### テストオプション
```bash
# 詳細表示
python manage.py test --verbosity=2

# 並列実行（高速化）
python manage.py test --parallel

# 失敗したテストのみ再実行
python manage.py test --failed

# 特定のパターンにマッチするテストのみ実行
python manage.py test --pattern="test_*.py"

# テストデータベースを保持（デバッグ用）
python manage.py test --keepdb
```

## テストカバレッジの確認

### coverageのインストール
```bash
pip install coverage
```

### カバレッジの実行
```bash
# テスト実行とカバレッジ測定
coverage run --source='.' manage.py test

# カバレッジレポートの表示
coverage report

# HTMLレポートの生成
coverage html
# ブラウザで htmlcov/index.html を開く
```

## テストの種類

### 1. モデルテスト
- データベースの操作が正しく動作するか
- モデルの制約やバリデーションが機能するか
- 関連フィールドの動作確認

### 2. ビューテスト
- ページが正常に表示されるか
- ログインが必要なページの保護
- フォーム送信後の動作確認

### 3. フォームテスト
- フォームのバリデーション
- エラーメッセージの表示
- 正常なデータの処理

### 4. 統合テスト
- 複数の機能を組み合わせた動作確認
- ユーザーの実際の操作フロー

## テストの活用ポイント

### 開発時
- 新機能追加時の動作確認
- リファクタリング後の動作確認
- バグ修正後の回帰テスト

### デプロイ時
- 本番環境への移行前の最終確認
- CI/CDパイプラインでの自動テスト
- コードの品質保証

### 保守時
- 依存関係の更新後の動作確認
- セキュリティパッチ適用後の確認
- パフォーマンス改善後の動作確認

## テストの書き方のコツ

### 1. テストケースの命名
```python
def test_user_can_login_with_valid_credentials(self):
    """有効な認証情報でユーザーがログインできるかテスト"""
    pass

def test_user_cannot_login_with_invalid_credentials(self):
    """無効な認証情報ではログインできないかテスト"""
    pass
```

### 2. setUpメソッドの活用
```python
def setUp(self):
    """テスト前の準備"""
    self.user = User.objects.create_user(
        username='testuser',
        password='testpass123'
    )
    self.client = Client()
```

### 3. アサーションメソッドの使い分け
```python
# 等価性の確認
self.assertEqual(actual, expected)

# 真偽値の確認
self.assertTrue(condition)
self.assertFalse(condition)

# Noneの確認
self.assertIsNone(value)
self.assertIsNotNone(value)

# 例外の確認
self.assertRaises(ValueError, function, arg)
```

## よくある問題と対処法

### 1. テストデータベースの問題
```bash
# テストデータベースを削除して再作成
python manage.py test --keepdb
```

### 2. 静的ファイルの問題
```bash
# 静的ファイルを収集
python manage.py collectstatic --noinput
```

### 3. マイグレーションの問題
```bash
# マイグレーションをリセット
python manage.py migrate --fake-initial
```

## 継続的インテグレーション（CI）

### GitHub Actionsの例
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python manage.py test
```

## 参考資料
- [Django公式テストドキュメント](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Djangoテストベストプラクティス](https://docs.djangoproject.com/en/stable/topics/testing/best-practices/)
- [Python unittest モジュール](https://docs.python.org/ja/3/library/unittest.html)

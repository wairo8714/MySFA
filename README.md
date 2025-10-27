# MySFA
営業活動を、もっとスマートに。グループの成果をリアルタイム共有・管理可能にするSFAツール。

<br />

# URL
お名前(ニックネーム可)、パスワードの登録のみで利用できます。<br />
https://mysfa.net

<br />

# 【営業職の皆様へ】こんなことでお困りではありませんか？

- 成績トップのAさんが、どんな営業をしているか分からない…
- 売り出し中のあの商品、みんなはどうやって営業をかけているんだろう？
- 営業先の業態は、どんなものが採用されているのか気になる…

<br />

# MySFAで営業を成功に導く

MySFAは、営業成果共有・分析に特化したSNS型webアプリケーションです。

- グループメンバーの営業活動記録をリアルタイムで共有・分析
- 活動記録は、商品/業態/ユーザーごとに検索可能
- グループの成果をグラフで「見える化」し、営業スタイルの改善に活かせる

<br />

# 実装機能一覧

## 基本設計

### デザイン/UI
-	堅実な印象を与えるライトグレー(#EDF0F1)をメインカラーに配し、ライトブルー(#3AADC8)をサブカラーに採用　ビジネス用途向けのシンプルさと、アプリがもたらす新しい営業のスタイルを表現
- サイドメニュー内に全機能を格納し、快適なアクセスを実現
- レスポンシブデザイン対応

<br />

###　グループ機能
- いずれかのグループへの所属が前提　所属グループのみタイムラインで閲覧可能
- 外部からグループ情報閲覧を制限する【ロック機能】搭載　非公開営業活動も共有可能

<br />

## 投稿画面

### 投稿フォーム
- 入力項目:商品名/業態名/営業内容/所属グループ/画像(任意)
- 入力必須項目はバリデーションチェック付き
- 上限文字数を常時表示　入力文字数はリアルタイムで反映

<br / >

### タイムライン
- すべての投稿/グループごとの投稿を選択して、タイムラインに表示可能
- 他ユーザーの投稿から、直接該当ユーザーの詳細ページに遷移可能
- Goodボタン機能搭載　あえて反応者の人数のみ確認可能にすることで、投稿のモチベーションアップと、グループ間でのコミュニケーション環境醸成の両立を図りたい

<br />

## 検索機能

### 検索対象
- 商品
- 業態
- グループ
- ユーザー

<br />

## マイページ(ユーザー詳細画面)

### ユーザー情報編集機能
 - ユーザーアイコン,ユーザー名を即座に変更可能
 - 他ユーザー閲覧時は、編集UI非表示で統一感維持

<br />

### グループ情報機能
- 所属グループを一覧表示
- グループ検索、作成ページへのリンクボタンを配置

<br />

### 営業成果レポート機能
- 商品別、業態別の営業成果を表示
- 期間指定機能搭載で、週・月単位の分析が可能

<br />

### 投稿一覧機能
- 投稿履歴をグループごとに絞り込み表示

<br />

## グループ詳細画面

### グループ作成者権限機能
- 作成者に限り、グループの削除、ロック機能のON/OFF、参加者の強制退会等の処理が可能
- 作成者が退会した場合、グループ参加順に権限が自動的に移動

<br/>

### グループ内営業成果レポート機能
- マイページと同様の機能に、メンバー全体の成果状況を閲覧可能

<br />


## 🛠️ 技術スタック

### フロントエンド
- **HTML5/CSS3**: レスポンシブデザイン
- **JavaScript**: インタラクティブなUI
- **Bootstrap**: モダンなUIコンポーネント

### バックエンド
- **Django 5.0.14**: Webフレームワーク
- **Python 3.12**: プログラミング言語
- **SQLite**: データベース（開発環境）
- **WhiteNoise**: 静的ファイル配信

### インフラストラクチャ
- **AWS EC2**: クラウドサーバー
- **Docker**: コンテナ化
- **Nginx**: リバースプロキシ・SSL終端
- **Let's Encrypt**: SSL証明書
- **Route 53**: DNS管理

### 開発・運用
- **GitHub Actions**: CI/CD
- **Terraform**: Infrastructure as Code
- **Docker Compose**: ローカル開発環境

## 🚀 セットアップ

### 前提条件
- Python 3.12+
- Docker & Docker Compose
- AWS CLI
- Terraform

### ローカル開発環境

1. **リポジトリのクローン**
```bash
git clone https://github.com/yourusername/mysfa_rebuild.git
cd mysfa_rebuild
```

2. **Docker Composeで起動**
```bash
docker-compose up -d
```

3. **データベースマイグレーション**
```bash
docker-compose exec app python manage.py migrate
```

4. **スーパーユーザー作成**
```bash
docker-compose exec app python manage.py createsuperuser
```

5. **アプリケーションにアクセス**
```
http://localhost:8000
```

### 本番環境デプロイ

1. **Terraformでインフラ構築**
```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```

2. **アプリケーションのデプロイ**
```bash
./deploy.sh
```

## 🏗️ インフラストラクチャ構成

### アーキテクチャ概要
```
Internet → Route 53 → EC2 (Nginx) → Docker Container (Django)
                    ↓
              Security Group (443, 80, 22)
                    ↓
              Let's Encrypt SSL
```

### セキュリティ設計
1. **外部からのアクセス**: HTTPS(443)のみ許可
2. **内部通信**: Nginx → Django (localhost:8000)
3. **SSHアクセス**: 特定IPアドレスからのみ許可
4. **SSL終端**: NginxでSSL処理、DjangoはHTTPで動作

### インフラ設定ファイル
- `main.tf`: EC2、セキュリティグループ、キーペアの定義
- `variables.tf`: 設定可能な変数（セキュリティ、アプリ設定）
- `outputs.tf`: デプロイ後の出力情報
- `user_data.sh`: EC2起動時の初期化スクリプト
- `nginx.conf`: Nginxリバースプロキシ設定

### セキュリティベストプラクティス
- **最小権限の原則**: 必要最小限のポートのみ開放
- **多層防御**: セキュリティグループ + ファイアウォール + アプリケーション
- **暗号化**: 通信の暗号化（HTTPS）とデータの暗号化
- **監視**: ログ収集とローテーション設定

## 📁 プロジェクト構造

```
mysfa_rebuild/
├── src/                    # Djangoアプリケーション
│   ├── accounts/          # ユーザー管理
│   ├── mysfa/             # メインアプリケーション
│   ├── config/            # 設定ファイル
│   ├── static/            # 静的ファイル
│   ├── template/          # テンプレート
│   └── manage.py          # Django管理スクリプト
├── infrastructure/        # インフラ設定
│   ├── terraform/        # Terraform設定
│   │   ├── main.tf       # メイン設定
│   │   ├── variables.tf  # 変数定義
│   │   ├── outputs.tf    # 出力定義
│   │   └── terraform.tfvars # 変数値
│   ├── keys/             # SSH鍵
│   │   └── mysfa-dev-keypair*
│   └── config/           # 設定ファイル
│       ├── user_data.sh  # EC2初期化スクリプト
│       └── nginx.conf    # Nginx設定
├── docker/               # Docker設定
│   └── Dockerfile        # コンテナ定義
├── .github/              # GitHub Actions
│   └── workflows/        # CI/CD設定
└── README.md             # このファイル
```

## 🔧 開発

### テスト実行
```bash
python src/manage.py test
python src/manage.py check
```

### コードフォーマット
```bash
black src/
isort src/
flake8 src/
```

### データベースリセット
```bash
python src/manage.py flush
python src/manage.py migrate
```

## 🌐 デプロイメント

### 自動デプロイ
- `main`ブランチへのプッシュで自動デプロイ
- GitHub Actionsがテスト→ビルド→デプロイを実行

### 手動デプロイ
```bash
./deploy.sh
```

## 🔒 セキュリティ

### インフラストラクチャセキュリティ
- **Nginxリバースプロキシ**: アプリケーションを内部ネットワークに隔離
- **ポート制限**: 8000番ポートを外部に公開せず、443(HTTPS)のみ開放
- **SSHアクセス制限**: 特定IPアドレスからのみSSH接続を許可
- **ファイアウォール**: firewalldによる追加のセキュリティ層

### アプリケーションセキュリティ
- **HTTPS強制**: HTTPからHTTPSへの自動リダイレクト
- **SSL/TLS**: Let's Encrypt SSL証明書（自動更新）
- **セキュリティヘッダー**: 
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- **Djangoセキュリティ**: CSRF保護、XSS保護、SQLインジェクション対策

### セキュリティ設定の詳細
```hcl
# SSHアクセス制限（variables.tf）
variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH access"
  type        = list(string)
  default     = ["0.0.0.0/0"]  # 本番環境では特定のIPに変更
}

# セキュリティグループ（main.tf）
resource "aws_security_group" "main" {
  # SSH - 特定IPからのみアクセス許可
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }
  
  # HTTPS - Nginxリバースプロキシ経由
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # 8000番ポートは削除（内部通信のみ）
}
```

## 📊 監視・ログ

- **Nginx アクセスログ**: `/var/log/nginx/access.log`
- **Django アプリケーションログ**: `django.log`
- **SSL証明書**: 自動更新設定済み

## 🤝 貢献

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

# MySFA

![ヘッダー画像](/docs/img/header/mysfa-header.png)

営業活動を、もっとスマートに。  
グループの成果をリアルタイムに共有・分析できる、営業職向け SNS 型 SFA ツールです。

<br />

## サービスのURL

お名前(ニックネーム可)、パスワードの登録のみでご利用いただけます。

https://mysfa.net

<br />

## サービスへの想い

私は、営業職として日々「人と人」「商品とお客様」をつなぐ仕事に携わってきました。  
その中で、こんな課題感を強く感じていました。

- トップセールスの「勝ちパターン」が、現場に共有されない
- せっかくの成功事例が、口頭ベースで流れていってしまう
- 「どの商品を」「どの業態に」提案すべきかを、感覚に頼りがち

**MySFA** は、

- 営業メンバーそれぞれの「成果」と「工夫」を見える化し、
- グループ全体で共有・分析できるようにすることで、

営業活動そのものを、もっと楽しく・もっと再現性のあるものにしたい、という想いから生まれました。

単なる「日報ツール」ではなく、  
**営業のノウハウが自然と蓄積される SNS** を目指しています。

<br />

## アプリケーションのイメージ

![アプリケーションのイメージ](/docs/img/app-view/mysfa-overview.gif)

> タイムライン投稿 → グループ別フィルタ → 成果グラフの確認、までの流れを 1 本の GIF で表現する想定です。

<br />

## 機能一覧

### 認証・トップ画面

| トップ画面 | ログイン / 新規登録画面 |
| --- | --- |
| ![トップ画面](/docs/img/app-view/top.png) | ![ログイン画面](/docs/img/app-view/login.png) |
| サービスの概要紹介と「新規登録」「ログイン」への導線を配置。営業職向けの世界観を、ヒーロービジュアルとコピーで表現しています。 | ログインID（メールアドレス）とパスワードで認証を実施。新規登録画面では、ユーザーIDや所属グループの選択も可能です。 |

<br />

### 投稿・タイムライン

| 投稿フォーム画面 | タイムライン画面 |
| --- | --- |
| ![投稿フォーム画面](/docs/img/app-view/post-form.png) | ![タイムライン画面](/docs/img/app-view/timeline.png) |
| 商品名 / 業態 / 営業内容 / グループ / 画像（任意）を入力して投稿できます。入力必須項目のバリデーションと、文字数カウンターを実装しています。 | グループメンバーの営業活動がタイムライン形式で表示されます。商品名・業態・グループごとに投稿を読み返し、成功パターンを素早く把握できます。 |

| グループフィルタ付きタイムライン | Goodボタン（リアクション） |
| --- | --- |
| ![グループフィルタ](/docs/img/app-view/timeline-filter.png) | ![Goodボタン](/docs/img/app-view/good-button.png) |
| 所属グループごとに投稿を絞り込み可能です。チーム単位での成功事例共有にフォーカスしたタイムラインとして利用できます。 | 投稿ごとに Good ボタンを実装。誰が押したかではなく「人数のみ」を表示する設計にすることで、気軽なリアクションと健全なモチベーションアップの両立を狙っています。 |

<br />

### 検索機能

| 商品・業態検索画面 | ユーザー / グループ検索画面 |
| --- | --- |
| ![商品・業態検索](/docs/img/app-view/search-products-customers.png) | ![ユーザー・グループ検索](/docs/img/app-view/search-users-groups.png) |
| 商品名・業態名で投稿を横断検索できます。「この商品はどの業態で売れている？」「この業態にはどの商品が効いている？」といった問いに素早く答えられます。 | ユーザーやグループを検索し、詳細ページへ遷移できます。新しいチームの活動を知る入口として機能します。 |

<br />

### マイページ / 成果レポート

| マイページ（プロフィール） | マイページ（個人成果レポート） |
| --- | --- |
| ![マイページプロフィール](/docs/img/app-view/mypage-profile.png) | ![個人成果レポート](/docs/img/app-view/mypage-report.png) |
| プロフィール画像・ユーザー名などを編集できます。他ユーザーから閲覧される際は編集 UI を非表示にし、見栄えを重視しています。 | 自分の投稿をもとに、商品別・業態別の成果をグラフ化して表示します。期間フィルタにより、週 / 月単位での振り返りが可能です。 |

<br />

### グループ機能

| グループ詳細画面 | グループレポート画面 |
| --- | --- |
| ![グループ詳細画面](/docs/img/app-view/group-detail.png) | ![グループレポート画面](/docs/img/app-view/group-report.png) |
| グループ名・説明・ロック状態（外部公開 / 非公開）などの情報を確認できます。作成者は、ロック機能やメンバーの強制退会などの権限を持ちます。 | グループ全体の成果を、商品別・業態別に可視化します。メンバーの活動の傾向や、重点商品・重点業態の把握に活用できます。 |

<br />

## 使用技術

| Category          | Technology Stack                                                                 |
| ----------------- | -------------------------------------------------------------------------------- |
| Frontend          | HTML5, CSS3, JavaScript (Vanilla), Chart.js                                     |
| Backend           | Python 3.12, Django 5.0.14, django-storages, gunicorn                           |
| Database          | MySQL（ローカル: Docker コンテナ, 本番: Amazon RDS for MySQL）                   |
| Storage           | Amazon S3（静的ファイル / メディアファイル）                                    |
| Infrastructure    | Amazon ECS (Fargate), Application Load Balancer, Amazon RDS, Amazon ECR, VPC, Security Group, Route 53, AWS IAM |
| Logging / Monitoring | Amazon CloudWatch Logs, ALB Access Logs                                      |
| IaC               | Terraform（VPC / ALB / ECS / RDS / S3 / ECR / IAM をモジュール化して管理）      |
| CI/CD             | GitHub Actions（Terraform Plan/Apply, Docker Build & Push, ECS デプロイ）       |
| Dev Environment   | Docker, Docker Compose, Poetry                                                  |
| Lint / Format     | flake8, black, isort                                                             |
| Design            | Figma（モック・レイアウト設計想定）                                             |

<br />

## システム構成図

![システム構成図](/docs/img/system-architecture/mysfa-architecture.png)

想定構成:

- Route 53 にて `mysfa.net` / `www.mysfa.net` を管理
- Application Load Balancer が HTTPS(443) を終端
- ALB から ECS Fargate 上の Django コンテナへルーティング（コンテナポート 80）
- ECS タスクから RDS(MySQL) への DB 接続
- 静的ファイル / メディアファイルは S3 に保存
- アプリケーションログ / ECS ログ / ALB アクセスログを CloudWatch Logs に集約

<br />

## ER 図

![ER図](/docs/img/entity-relationship-diagram/mysfa-er.png)

想定エンティティ（例）:

- `User`: カスタムユーザー（営業担当者）
- `Group`: 営業グループ
- `Post`: 営業活動の投稿（商品 / 業態 / 内容 / 添付画像）
- `Like`: Good ボタン（ユーザー × 投稿）
- `CustomerCategory`: 業態マスタ
- `Product`: 商品マスタ

などを中心とした構造になっています。

<br />

## 今後の展望

MySFA は、以下のようなフェーズを想定して拡張していく予定です。

- **フェーズ1:**  
  営業活動の投稿・共有機能、グループ機能、基本的なレポート機能（商品別 / 業態別）を実装（＝現在ここ）。
- **フェーズ2:**  
  タグ機能やコメント機能、より柔軟な検索・フィルタ機能を追加し、ナレッジ共有の幅を広げる。
- **フェーズ3:**  
  営業目標・KPI と紐づけたダッシュボード機能を実装し、達成状況をリアルタイムに可視化できるようにする。
- **フェーズ4:**  
  外部ツール（SFA / CRM / カレンダーなど）との連携を行い、営業活動の「ハブ」として機能する統合プラットフォームを目指す。

営業メンバー一人ひとりの工夫や成功体験が、チーム全体の成果に直結する世界を目指して、継続的に改善・開発を進めていきます。
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

<br />

## 機能一覧

| トップ画面 | ログイン / 新規登録画面 |
| --- | --- |
| ![トップ画面](/docs/img/app-view/top.png) | ![ログイン画面](/docs/img/app-view/login.png) |
| サービスの概要紹介と「新規登録」「ログイン」への導線を配置。営業職向けの世界観を、ヒーロービジュアルとコピーで表現しています。 | ユーザーIDとパスワードで認証を実施します。新規登録/パスワード再発行ページへのリンクも掲載しています。 |

<br />

| 投稿フォーム画面 | タイムライン画面 |
| --- | --- |
| ![投稿フォーム画面](/docs/img/app-view/post-form.png) | ![タイムライン画面](/docs/img/app-view/timeline.png) |
| 商品名 / 業態 / 営業内容 / グループ / 画像（任意）を入力して投稿できます。入力必須項目のバリデーションと、文字数カウンターを実装しています。 | グループメンバーの営業活動がタイムライン形式で表示されます。商品名・業態・グループごとに投稿を読み返し、成功パターンを素早く把握できます。 |

<br />

| 商品・業態検索画面 | グループ詳細画面 |
| --- | --- |
| ![商品・業態検索](/docs/img/app-view/search-products-customers.png) | ![グループ詳細画面](/docs/img/app-view/group-detail.png) |
| 商品名・業態名で投稿を横断検索できます。「この商品はどの業態で売れている？」「この業態にはどの商品が効いている？」といった問いに素早く答えられます。 | グループ名・説明・ロック状態（外部公開 / 非公開）などの情報を確認できます。作成者は、ロック機能やメンバーの強制退会などの権限を持ちます |

<br />

| マイページ（プロフィール） | マイページ（個人成果レポート） |
| --- | --- |
| ![マイページプロフィール](/docs/img/app-view/mypage-profile.png) | ![個人成果レポート](/docs/img/app-view/mypage-report.png) |
| プロフィール画像・ユーザー名などを編集できます。他ユーザーから閲覧される際は編集 UI を非表示にし、見栄えを重視しています。 | 自分の投稿をもとに、商品別・業態別の成果をグラフ化して表示します。期間フィルタにより、週 / 月単位での振り返りが可能です。 |

<br />

## 使用技術

## 使用技術

### フロントエンド

![HTML5](https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
![Chart.js](https://img.shields.io/badge/Chart.js-FF6384?logo=chartdotjs&logoColor=white)

### バックエンド

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django&logoColor=white)
![Gunicorn](https://img.shields.io/badge/Gunicorn-20.1-499848)
![django-storages](https://img.shields.io/badge/django--storages-👀-0A0A0A)

### データベース / ストレージ

![MySQL](https://img.shields.io/badge/MySQL-8.x-4479A1?logo=mysql&logoColor=white)
![Amazon RDS](https://img.shields.io/badge/Amazon%20RDS-MySQL-527FFF?logo=amazonrds&logoColor=white)
![Amazon S3](https://img.shields.io/badge/Amazon%20S3-Storage-569A31?logo=amazons3&logoColor=white)

### インフラ

![AWS](https://img.shields.io/badge/AWS-Cloud-232F3E?logo=amazonaws&logoColor=white)
![ECS Fargate](https://img.shields.io/badge/Amazon%20ECS-Fargate-FF9900?logo=amazonecs&logoColor=white)
![Application Load Balancer](https://img.shields.io/badge/AWS-ALB-FF4F8B)
![VPC](https://img.shields.io/badge/AWS-VPC-527FFF)
![Security Group](https://img.shields.io/badge/AWS-Security%20Group-232F3E)
![Route%2053](https://img.shields.io/badge/AWS-Route%2053-8C4FFF)
![IAM](https://img.shields.io/badge/AWS-IAM-DD344C)

### 開発環境 / その他

![Docker](https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-Web%20Server-009639?logo=nginx&logoColor=white)
![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?logo=terraform&logoColor=white)


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

![システム構成図](/docs/img/header/mysfa-architecture.png)

想定構成:

- Route 53 にて `mysfa.net` / `www.mysfa.net` を管理
- Application Load Balancer が HTTPS(443) を終端
- ALB から ECS Fargate 上の Django コンテナへルーティング（コンテナポート 80）
- ECS タスクから RDS(MySQL) への DB 接続
- 静的ファイル / メディアファイルは S3 に保存
- アプリケーションログ / ECS ログ / ALB アクセスログを CloudWatch Logs に集約

<br />

## ER 図

![ER図](/docs/img/header/mysfa-er.png)

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

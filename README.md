# MySFA

![ヘッダー画像](/docs/img/header/mysfa-header.png)

営業活動を、もっとスマートに。  
グループの成果をリアルタイムに共有・分析できる、営業職向け SNS 型 SFA ツールです。

<br />

## サービスのURL

お試しログイン(デモ)で、MySFAをご利用いただけます。

https://mysfa.net

<br />

## 最新アップデート
- **2026-01-27**: グループの管理者操作画面を追加しました。
- **2026-01-22**: 「お試しログイン」機能を追加しました。
- **2026-01-17**: 商品マスタ/業態マスタ機能を追加しました。

<br />

## ローカルでの起動方法

### 前提
- Docker / Docker Compose が利用できること

### セットアップ
```bash
git clone https://github.com/wairo8714/MySFA.git
cd MySFA
cp .env.example .env
docker compose up --build
```

### 初回セットアップ
```bash
docker compose exec web python src/manage.py migrate
```
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

| 投稿フォーム画面 | タイムライン画面 |
| --- | --- |
| ![投稿フォーム画面](/docs/img/app-view/post-form2.png) | ![タイムライン画面](/docs/img/app-view/timeline2.png) |
| 商品名 / 業態 / 営業内容 / グループ / 行動進捗 / 画像（任意）を入力して投稿できます。選択したグループのマスタから商品、業態を選択することができます。 |グループのメンバーの営業活動を閲覧したり、いいねボタンやコメント機能で、自分やメンバーとのコミュニケーションも可能です。 |

<br />

| 商品/業態マスタ画面 | グループ詳細画面 |
| --- | --- |
| ![商品・業態マスタ](/docs/img/app-view/master.png) | ![権限管理画面](/docs/img/app-view/admin.png) |
| グループマスタに、商品と業態を登録することで、投稿時に利用することができるようになります。一括削除機能や、csv一括登録機能を搭載し、スムーズなマスタ管理を可能にします。 | グループの権限を管理できます。付与・剥奪を直感的に操作でき、管理者のみが操作可能な機能を開放させることができます。 |

<br />

| 営業成果レポート | 投稿検索ページ |
| --- | --- |
| ![営業成果レポート](/docs/img/app-view/report.png) | ![投稿検索](/docs/img/app-view/search.png) |
| 採用された商品は、マイページとグループページにある「営業成果レポート」で振り返ることができます。期間指定が可能で、過去の成果もチェックできます。 | 対象グループや、検索一致条件、分類検索など、細やかな検索オプションを指定可能。目的の投稿へすぐにアクセスできます。 |

<br />

| お試しログイン機能 | グループロック機能 |
| --- | --- |
| ![お試しログイン](/docs/img/app-view/trial.png) | ![ロック機能](/docs/img/app-view/lock.png) |
| 登録情報を入力しなくても、ほぼ全ての機能をご利用いただける「お試しログイン」機能を搭載しています。MySFAの機能をお試しいただく際は、こちらをご利用ください。 | 秘匿性の高い情報も、MySFAなら守れます。ロック機能を使えば、管理者の許可がない限り、グループの閲覧や参加ができません。|

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
![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub%20Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?logo=terraform&logoColor=white)

<br />

## システム構成図

![システム構成図](/docs/img/header/mysfa-architecture.png)

### 構築 / デプロイ

- **①** コード変更をGitHubへpush (Django/Terraform/Dockerfile)
- **②** GitHub ActionsでTerraformを実行し、AWSリソースをを構築・更新
- **③** GitHub ActionsでDockerイメージをビルド→ECRへpush→ECSを更新(デプロイ)  
- **④** ECS起動時にECRからイメージをプルしてアプリを実行

### アプリ実行

- **⑤** Route53でドメインをALBに名前解決
- **⑥** クライアント→Internet→ALBにHTTPSで到達
- **⑦** ALB→ECSタスクに転送  
- **⑧** ECS→RDS(MySQL)に接続してデータ読み書き
- **⑨** ECS→S3に静的/メディアを保存・取得

<br />

## ER 図

![ER図](/docs/img/header/mysfa-er.png)

<br />

## 今後の展望

MySFA は、以下のようなフェーズを想定して段階的に拡張していく予定です。

- **フェーズ1**  
  営業活動の投稿・共有機能、グループ機能、商品別/業態別の基本的なレポート機能を実装。

- **フェーズ2 **  
  商品・業態専用のマスタテーブルを新設し、登録用ページも実装。  
  投稿・検索時に入力のしやすさとデータの一貫性を高めます。

- **フェーズ3 (現在)**  
  フロントエンドをTypeScriptとモダンなフレームワーク（Vue/Reactなど）で再構築し、  
  コンポーネント指向のUIと高速なレスポンスで、よりリッチで使いやすい画面体験を目指します。

- **フェーズ4**  
  レポート画面を拡張し、ダッシュボード機能を実装。  
  営業成果や活動傾向をグラフ・指標としてまとめて表示し、より直感的に状況を把握できるようにします。

  

- **フェーズ5**  
  外部ツール（SFA/CRM/カレンダーなど）との連携機能を追加し、  
  営業活動データの「ハブ」として機能する統合プラットフォームを目指します。

営業メンバーの工夫や成功体験が、チーム全体の成果に直結する世界を目指し、今後も継続的に改善・開発を進めていきます。

## 開発記事（Qiita）

開発の背景（営業現場の課題）から、学習〜実装、実運用して見えた良かった点/苦労した点までをQiitaにまとめました。  
- [ルートセールスがSFAを"作る"まで ─ 現場の課題から始まったゼロからのWebアプリ開発](https://qiita.com/wairo8714/items/ab64ee36252c9444689a)

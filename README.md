# unpaywall-skill

Claude用のSkillです。[Unpaywall](https://unpaywall.org/) のAPIを使い、DOIから論文の合法的なオープンアクセス版を探して、必要ならPDFを保存します。

Unpaywallの公式ツールではありません。ペイウォールやCAPTCHAを回避する機能はありません。

## 必要なもの

- Claude Code
- Python 3.8以上（追加パッケージは不要）
- 自分のメールアドレス（Unpaywall APIの利用者識別に使います）

## インストール

macOS / Linux:

```bash
git clone https://github.com/masa-med-ai/unpaywall-skill.git
mkdir -p ~/.claude/skills
cp -R unpaywall-skill/unpaywall ~/.claude/skills/
```

Windows（PowerShell）:

```powershell
git clone https://github.com/masa-med-ai/unpaywall-skill.git
New-Item -ItemType Directory -Force "$env:USERPROFILE\.claude\skills"
Copy-Item -Recurse unpaywall-skill\unpaywall "$env:USERPROFILE\.claude\skills\"
```

## 初回設定

初めて使うと、Claudeがメールアドレスの設定を案内します。先に設定する場合は次を実行し、Claudeを再起動してください。

macOS（zsh）:

```bash
echo 'export UNPAYWALL_EMAIL="you@your-domain"' >> ~/.zshrc
```

Linux（bash）:

```bash
echo 'export UNPAYWALL_EMAIL="you@your-domain"' >> ~/.bashrc
```

Windows（PowerShell）:

```powershell
setx UNPAYWALL_EMAIL "you@your-domain"
```

## 使い方

Claudeに次のように頼みます。

- 「10.1136/bmj.n71 のOA版を探して」
- 「このDOIのPDFをダウンロードして」

## 制限

- 出版社のボット対策により、OA論文でもPDFを自動保存できないことがあります。その場合は論文ページのリンクから取得してください。
- Windowsでの動作は未検証です。

## ライセンス

[MIT License](LICENSE)

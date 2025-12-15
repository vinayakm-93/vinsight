# How to Contribute (Fork & Pull Request Workflow)

This guide explains how others can contribute to your project.

## 1. Fork the Repository
Contributors should click the **"Fork"** button in the top-right corner of your GitHub repository page (`vinayakm-93/vinsight`). This creates a copy in their own account.

## 2. Clone their Fork
They run this in their terminal (replacing `their-username`):

```bash
git clone https://github.com/their-username/vinsight.git
cd vinsight
```

## 3. Create a Branch
Best practice is to create a new branch for each feature:

```bash
git checkout -b feature/my-new-feature
```

## 4. Make Changes & Push
They edit files, then verify, commit, and push:

```bash
git add .
git commit -m "Add cool new feature"
git push origin feature/my-new-feature
```

## 5. Create Pull Request (PR)
1. They go to **your** repository on GitHub.
2. They will see a banner saying "Compare & pull request".
3. They click it, describe their changes, and submit.

## 6. You Review & Merge
1. You go to the **"Pull requests"** tab in your repo.
2. Click the new request.
3. Review the code changes.
4. Click **"Merge pull request"** to add their code to your main branch.

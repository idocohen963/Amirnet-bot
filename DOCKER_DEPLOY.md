# 🚀 מדריך פריסה מהירה ל-Docker

## שלבים:

### 1️⃣ הכן את הסביבה
```bash
# וודא שיש לך קובץ .env עם הטוקן
echo "TELEGRAM_TOKEN=your_bot_token_here" > .env
```

### 2️⃣ בנה את הקונטיינר
```bash
# אופציה 1: עם docker-compose (מומלץ)
docker-compose up -d --build

# אופציה 2: עם Docker ישיר
docker build -t nite-checker .
docker run -d --name nite_bot --env-file .env -v $(pwd)/exams_data.db:/app/exams_data.db nite-checker
```

### 3️⃣ בדוק שהכל עובד
```bash
# צפה בלוגים
docker-compose logs -f

# בדוק סטטוס
docker-compose ps

# בדוק שהבוטים רצים
docker exec -it nite_checker_bot ps aux
```

### 4️⃣ ניהול הקונטיינר
```bash
# עצור
docker-compose down

# הפעל מחדש
docker-compose restart

# עדכן קוד ובנה מחדש
git pull
docker-compose up -d --build
```

---

## 📦 העלאה לענן

### Docker Hub (שיתוף ציבורי)
```bash
docker login
docker tag nite-checker:latest yourusername/nite-checker:latest
docker push yourusername/nite-checker:latest
```

### AWS ECR (פרטי)
```bash
# התחבר ל-ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# צור repository
aws ecr create-repository --repository-name nite-checker

# העלה
docker tag nite-checker:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/nite-checker:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nite-checker:latest
```

### הרצה ב-VPS (Digital Ocean / Linode / AWS EC2)
```bash
# SSH לשרת
ssh user@your-server

# התקן Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# התקן Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# העתק את הפרויקט
git clone your-repo-url
cd nite_checker

# צור .env
nano .env
# הוסף: TELEGRAM_TOKEN=your_token

# הרץ
docker-compose up -d

# (אופציונלי) הגדר auto-start בבוט
sudo systemctl enable docker
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

צור `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build Docker image
        run: docker build -t nite-checker .
      
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /app/nite_checker
            git pull
            docker-compose up -d --build
```

---

## ⚙️ הגדרות נוספות

### שמירת לוגים
הוסף ל-`docker-compose.yml`:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

### Healthcheck
```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import requests; requests.get('https://api.telegram.org')"]
  interval: 1m
  timeout: 10s
  retries: 3
```

### Environment Variables בענן
במקום `.env`, השתמש ב-secrets של הפלטפורמה:
- AWS: Parameter Store / Secrets Manager
- GCP: Secret Manager
- Azure: Key Vault
- Heroku/Railway: Dashboard Settings

---

## 🧹 תחזוקה

```bash
# נקה images ישנים
docker system prune -a

# גבה את מסד הנתונים
docker cp nite_checker_bot:/app/exams_data.db ./backup_$(date +%Y%m%d).db

# שחזר מסד נתונים
docker cp ./backup.db nite_checker_bot:/app/exams_data.db
docker-compose restart
```

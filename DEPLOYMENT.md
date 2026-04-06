# 🚀 Deployment Instructions - Render.com

## ✅ Prerequisites Complete

Your code is ready for deployment! All configuration files are in place.

---

## 📋 Step-by-Step Deployment

### **Step 1: Sign Up for Render** (2 min)

1. Go to https://render.com
2. Click "Get Started for Free"
3. Sign up with your GitHub account
4. Authorize Render to access your repositories

---

### **Step 2: Create New Web Service for Backend** (5 min)

1. Click "New +" → "Web Service"
2. Connect your GitHub repository: `Hexinator12/Voice-RAG`
3. Configure the service:

**Settings:**
- **Name:** `voicerag-backend`
- **Region:** Oregon (US West)
- **Branch:** `main`
- **Root Directory:** (leave empty)
- **Environment:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Plan:** Free

4. Click "Advanced" and add Environment Variables:

**Environment Variables:**
```
GEMINI_API_KEY = your_gemini_api_key_here
```

**For Google Cloud TTS:**
```
GOOGLE_APPLICATION_CREDENTIALS = paste_your_google_cloud_json_here
```

5. Click "Create Web Service"
6. Wait for deployment (5-10 min)
7. **Copy the URL** (e.g., `https://voicerag-backend.onrender.com`)

---

### **Step 3: Create Static Site for Frontend** (5 min)

1. Click "New +" → "Static Site"
2. Connect same repository: `Hexinator12/Voice-RAG`
3. Configure the site:

**Settings:**
- **Name:** `voicerag-frontend`
- **Branch:** `main`
- **Root Directory:** (leave empty)
- **Build Command:** `cd frontend && npm install && npm run build`
- **Publish Directory:** `frontend/dist`

4. Add Environment Variable:

**Environment Variables:**
```
VITE_API_URL = https://voicerag-backend.onrender.com
```
(Use the backend URL from Step 2)

5. Click "Create Static Site"
6. Wait for deployment (5-10 min)
7. **Copy the URL** (e.g., `https://voicerag-frontend.onrender.com`)

---

## 🎉 Your App is Live!

**Frontend URL:** `https://voicerag-frontend.onrender.com`
**Backend URL:** `https://voicerag-backend.onrender.com`

---

## 🧪 Testing Your Deployment

1. Open the frontend URL in your browser
2. Wait ~30 seconds for backend to wake up (first time)
3. Test features:
   - ✅ Select language
   - ✅ Ask a question
   - ✅ Try voice input
   - ✅ Switch languages
   - ✅ Check voice output

---

## ⚠️ Important Notes

### **Free Tier Limitations:**
- Backend sleeps after 15 min of inactivity
- Takes ~30 seconds to wake up on first request
- 750 hours/month (enough for demos)

### **For Your Presentation:**
- **Ping the URL 5 minutes before demo** to wake it up
- Keep a tab open during presentation
- Have local backup ready

### **To Keep It Awake:**
Use a ping service like:
- https://cron-job.org
- https://uptimerobot.com
- Ping every 10 minutes

---

## 🔧 Troubleshooting

### **Backend Not Responding:**
- Check logs in Render dashboard
- Verify environment variables are set
- Check if service is sleeping

### **Frontend Can't Connect:**
- Verify `VITE_API_URL` is correct
- Check CORS settings in backend
- Wait for backend to wake up

### **Build Failures:**
- Check build logs in Render
- Verify all dependencies in requirements.txt
- Check Node version compatibility

---

## 📊 Monitoring

**Render Dashboard:**
- View logs
- Check metrics
- Monitor uptime
- See deployment history

---

## 🎓 For Capstone

**Share These URLs:**
- Frontend: `https://voicerag-frontend.onrender.com`
- GitHub: `https://github.com/Hexinator12/Voice-RAG`

**Demo Tips:**
1. Open URL 5 min before presentation
2. Test all features beforehand
3. Show GitHub repo
4. Explain architecture
5. Demonstrate all 5 languages

---

## 💰 Cost

**Current:** $0/month (Free tier)

**If You Need Always-On:**
- Upgrade backend to $7/month
- Frontend stays free
- No sleep time
- Better for production

---

## ✅ Deployment Checklist

- [ ] Signed up for Render
- [ ] Created backend web service
- [ ] Added environment variables
- [ ] Backend deployed successfully
- [ ] Created frontend static site
- [ ] Frontend deployed successfully
- [ ] Tested all features
- [ ] Shared URLs with evaluators

---

**Your Voice RAG is now publicly accessible!** 🚀

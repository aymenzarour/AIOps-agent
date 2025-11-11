# 🤖 K3s Gemini AIOps Agent

This project is a **lightweight AIOps agent** designed for Kubernetes (specifically **K3s**).  
It actively monitors cluster events and uses the **Google Gemini API** for AI-driven analysis of any problems.

When a workload fails (e.g., `ImagePullBackOff`, `CrashLoopBackOff`), this agent automatically detects the event, queries the Gemini API for a simple explanation, and sends a **concise alert to a Telegram chat**.

---

## 💡 Core Idea & Optimization

The main idea is to get **simple, AI-powered, and actionable alerts** instead of raw, cryptic Kubernetes error messages.

A key optimization is the **anti-spam cache**.  
The `agent.py` script maintains an in-memory `set()` of already-reported problems (based on a `namespace/pod/reason` key).  
This ensures that if a pod is in a `CrashLoopBackOff` loop, you only get **one alert** for that specific failure, not hundreds.

---

## 📁 Project Structure

The project is organized into two main parts: the Python application source code and the Kubernetes deployment manifests.

```
├── app/                 # Contains the agent's source code
│   ├── Dockerfile       # Builds the agent's container image
│   ├── agent.py         # The main Python agent logic
│   └── requirements.txt # Python libraries
├── deployments.yaml     # Kubernetes Deployment for the agent
├── rbac.yaml            # Kubernetes permissions (ServiceAccount, Role)
└── test_fail.yaml       # A sample pod to test the agent
```

---

## 🚀 Deployment Guide

Follow these steps to deploy the agent to your cluster.

---

### **Step 1: Get Your Secrets**

You need three secret keys.

#### **Google Gemini API Key**
1. Go to the **Google Cloud Console**.  
2. Create a new project.  
3. Go to **Billing** and link a billing account (required even for free-tier usage).  
4. Go to **APIs & Services → Library**.  
5. Search for and enable **Vertex AI Generative AI API**.  
6. Go to **APIs & Services → Credentials**, and create a new **API Key**.

#### **Telegram Bot Token**
1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather).  
2. Type `/newbot`, follow the prompts, and copy the API Token it gives you.

#### **Telegram Chat ID**
1. Start a chat with [@userinfobot](https://t.me/userinfobot).  
2. Type `/start` and it will reply with your **Chat ID**.

---

### **Step 2: Apply RBAC Permissions**

The agent needs permission to read cluster events.  
This file (`rbac.yaml`) creates a ServiceAccount for it.

```bash
kubectl apply -f rbac.yaml
```

---

### **Step 3: Create the Kubernetes Secret**

Store your keys securely in the cluster.  
The key names (`GEMINI_API_KEY`, etc.) must match exactly, as the Python script relies on them.

```bash
kubectl create secret generic ai-agent-secrets   --from-literal=GEMINI_API_KEY='PASTE_YOUR_GEMINI_KEY_HERE'   --from-literal=TELEGRAM_BOT_TOKEN='PASTE_YOUR_TELEGRAM_TOKEN_HERE'   --from-literal=TELEGRAM_CHAT_ID='PASTE_YOUR_TELEGRAM_CHAT_ID_HERE'
```

---

### **Step 4: Build and Push the Docker Image**

Navigate to the `app/` directory and build your container.

```bash
# cd into the app directory
cd app/

# Build the image (replace with your Docker Hub username)
docker build -t your-dockerhub-username/ai-agent:v7 .

# Push the image to the registry
docker push your-dockerhub-username/ai-agent:v7
```

---

### **Step 5: Deploy the Agent**

Before you deploy, edit the `deployments.yaml` file.

1. Open `deployments.yaml`.  
2. Find the line:
   ```yaml
   image: ...
   ```
3. Replace it with your image:
   ```yaml
   image: your-dockerhub-username/ai-agent:v7
   ```
4. Save and deploy:

```bash
kubectl apply -f deployments.yaml
```

---

### **Step 6: Verify the Agent**

Check that your agent is running and view its logs:

```bash
# Get the pod name (it will have a random hash)
kubectl get pods -l app=ai-agent

# Follow the logs for that pod
kubectl logs -f <name-of-your-agent-pod>
```

You should see something like:

```
--- Searching for compatible Gemini models (v7)... ---
--- Model selected (v7): ... ---
Starting K3s event surveillance...
```

---

## 🧪 How to Test

Once the agent is running, you can test it by applying the `test_fail.yaml` manifest, which tries to pull an image that doesn’t exist.

```bash
kubectl apply -f test_fail.yaml
```

Within a minute, Kubernetes will fail to pull the image, create a `Warning` event, and your agent should send you a **Telegram message**.

To clean up the test:

```bash
kubectl delete pod test-pod-fail
```

---

✅ **Result:**  
You now have an AI-powered monitoring agent that makes your **K3s cluster smarter**, giving you meaningful alerts directly on Telegram.

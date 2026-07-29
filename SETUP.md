# MPSC IT Club — Complete Setup Guide

> **For:** School administrators, club moderators, and technical handover  
> **Project:** MPSC IT Club Website  
> **Stack:** Python (Flask) · Supabase (Database + Storage) · Render (Hosting)

---

## Table of Contents

1. [What This Website Does](#1-what-this-website-does)
2. [Prerequisites](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [Step 1 — Clone the Repository](#step-1--clone-the-repository)
5. [Step 2 — Set Up the Database (Supabase)](#step-2--set-up-the-database-supabase)
6. [Step 3 — Configure Environment Variables](#step-3--configure-environment-variables)
7. [Step 4 — Run Locally](#step-4--run-locally)
8. [Step 5 — Deploy to the Internet (Render)](#step-5--deploy-to-the-internet-render)
9. [Admin Panel Guide](#admin-panel-guide)
10. [EC Member QR Codes](#ec-member-qr-codes)
11. [Adding Content](#adding-content)
12. [Troubleshooting](#troubleshooting)

---

## 1. What This Website Does

The MPSC IT Club website is a full-stack web application with the following pages and features:

| Page | URL | Description |
|------|-----|-------------|
| Home | `/` | Landing page with club intro |
| About | `/about` | Club history, EC timeline, achievements |
| EC Panel | `/ec-panel` | Executive Committee members by year |
| Gallery | `/gallery` | Photo gallery |
| Events | `/events` | Club events |
| Programs | `/programs` | Past programs |
| Contact | `/contact` | Contact information |
| Member Card | `/member/<id>` | Digital ID card (opened via QR code) |
| Dashboard | `/user/dashboard` | Logged-in member dashboard |
| Admin | `/admin` | Admin-only control panel |

**Key features:**
- Member registration and login system
- Admin panel to manage EC members, events, gallery, and payments
- QR codes for EC member ID cards (generated in admin panel, downloadable)
- Digital member card page accessible by scanning a QR code
- Supabase (cloud database + file storage) backend

---

## 2. Prerequisites

Before starting, make sure you have these installed on your computer:

| Tool | Download Link | Purpose |
|------|---------------|---------|
| **Python 3.10+** | https://www.python.org/downloads/ | Runs the website |
| **Git** | https://git-scm.com/downloads | Downloads the code |
| **pip** | Included with Python | Installs Python packages |

You also need **free accounts** on:
- **GitHub** — https://github.com (to store the code)
- **Supabase** — https://supabase.com (free database)
- **Render** — https://render.com (free hosting)

---

## 3. Project Structure

```
mpsc-it-club/
|
+-- backend/
|   +-- app.py                  <- Main Flask application
|   +-- config/
|   |   +-- db.py               <- Supabase database connection
|   +-- models/
|   |   +-- user.py             <- User model
|   +-- routes/
|   |   +-- admin_routes.py     <- Admin panel API
|   |   +-- auth_routes.py      <- Login / Signup / Password reset
|   |   +-- event_routes.py     <- Events API
|   |   +-- payment_routes.py   <- Payment/registration API
|   |   +-- user_routes.py      <- Public data API
|   +-- static/
|   |   +-- css/                <- Stylesheets
|   |   +-- js/                 <- JavaScript files
|   |   +-- assets/             <- Images, fonts
|   +-- templates/
|       +-- index.html          <- Home page
|       +-- about.html          <- About page
|       +-- ec-panel.html       <- EC Panel
|       +-- admin.html          <- Admin dashboard
|       +-- member_card.html    <- QR-linked digital ID card
|       +-- components/         <- Navbar, footer (shared)
|
+-- .env                        <- Secret keys (DO NOT share publicly)
+-- requirements.txt            <- Python dependencies
+-- Procfile                    <- Render startup command
+-- run_server.py               <- App entry point
+-- runtime.txt                 <- Python version for Render
```

---

## Step 1 — Clone the Repository

Open a terminal (Command Prompt or PowerShell on Windows) and run:

```bash
git clone https://github.com/YOUR_USERNAME/mpsc-it-club.git
cd mpsc-it-club
```

Then install all Python dependencies:

```bash
pip install -r requirements.txt
```

> If `pip` is not found, try `pip3` instead.

---

## Step 2 — Set Up the Database (Supabase)

This website uses **Supabase** as its database and file storage.

### 2.1 — Create a Supabase Project

1. Go to https://supabase.com and sign up (free)
2. Click **"New Project"**
3. Give it a name like `mpsc-it-club`
4. Set a strong database password (save it somewhere safe)
5. Choose a region close to Bangladesh (e.g., Singapore)
6. Click **"Create new project"** and wait ~2 minutes

### 2.2 — Get Your API Keys

Once your project is created:
1. In the left sidebar, click **Settings** then **API**
2. Copy these two values:
   - **Project URL** (looks like `https://xxxxxx.supabase.co`)
   - **service_role key** (under "Project API keys" — use **service_role**, NOT anon)

> WARNING: The service_role key has full database access. Never put it in public code or share it. Keep it only in your .env file.

### 2.3 — Create the Database Tables

In Supabase, go to **SQL Editor** and run each block below one at a time.

#### Table 1: users
```sql
create table users (
  id uuid default gen_random_uuid() primary key,
  full_name text not null,
  email text unique not null,
  password_hash text not null,
  role text default 'member',
  student_id text,
  section text,
  phone text,
  institution text,
  join_date timestamp default now()
);
```

#### Table 2: ec_members
```sql
create table ec_members (
  id uuid default gen_random_uuid() primary key,
  name text not null,
  designation text not null,
  category text not null,
  image_path text,
  facebook text,
  instagram text,
  website text,
  whatsapp text,
  display_order integer default 99,
  created_at timestamp default now()
);
```

NOTE — category field format: YEAR_SECTION, e.g. 2026_BVB, 2025_EVG.
Sections: BVB (Bangla Version Boys), BVG (Bangla Version Girls), EVB (English Version Boys), EVG (English Version Girls).

#### Table 3: events
```sql
create table events (
  id uuid default gen_random_uuid() primary key,
  title text not null,
  description text,
  date date,
  venue text,
  status text default 'Upcoming',
  banner text,
  fee integer default 0,
  created_at timestamp default now()
);
```

#### Table 4: programs
```sql
create table programs (
  id uuid default gen_random_uuid() primary key,
  title text not null,
  description text,
  date date,
  banner text,
  created_at timestamp default now()
);
```

#### Table 5: gallery
```sql
create table gallery (
  id uuid default gen_random_uuid() primary key,
  url text not null,
  caption text,
  category text default 'General',
  created_at timestamp default now()
);
```

#### Table 6: payments
```sql
create table payments (
  id uuid default gen_random_uuid() primary key,
  user_id uuid references users(id),
  event_id uuid references events(id),
  full_name text,
  phone text,
  email text,
  tx_id text,
  status text default 'pending',
  is_offline boolean default false,
  created_at timestamp default now()
);
```

### 2.4 — Create the Storage Bucket

1. In Supabase left sidebar, click **Storage**
2. Click **"New bucket"**
3. Name it exactly: `mpsc-it-club`
4. Check **"Public bucket"** so images are publicly viewable
5. Click **"Create bucket"**

### 2.5 — Set Storage Permissions

1. In Storage, click the `mpsc-it-club` bucket
2. Click the **"Policies"** tab
3. Click **"New Policy"** then **"For full customization"**
4. Set:
   - Policy name: `Allow all`
   - Allowed operation: SELECT, INSERT, UPDATE, DELETE
   - USING expression: `true`
   - WITH CHECK expression: `true`
5. Click **"Save policy"**

---

## Step 3 — Configure Environment Variables

In the root of the project folder, create a file called `.env`:

```
SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
SUPABASE_KEY=your_service_role_key_here
SECRET_KEY=choose_any_random_long_string_here
```

Replace:
- `SUPABASE_URL` with your Supabase Project URL from Step 2.2
- `SUPABASE_KEY` with your service_role key from Step 2.2
- `SECRET_KEY` with any random string (e.g. `MyClub2026SecretKey!`)

> IMPORTANT: Never share the .env file. Make sure it is listed in .gitignore.

---

## Step 4 — Run Locally

Start the website on your own computer:

```bash
python run_server.py
```

Open your browser and go to:
```
http://localhost:5000
```

### Create the First Admin Account

1. Go to `http://localhost:5000/auth/signup` and register a new account
2. Go to Supabase dashboard → Table Editor → `users` table
3. Find your row and change the `role` column from `member` to `admin`
4. Log out and log back in
5. You now have access to `http://localhost:5000/admin`

---

## Step 5 — Deploy to the Internet (Render)

### 5.1 — Push Code to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mpsc-it-club.git
git push -u origin main
```

### 5.2 — Create a Web Service on Render

1. Go to https://render.com and sign up (free)
2. Click **"New"** then **"Web Service"**
3. Connect your GitHub account and select the repository
4. Fill in these settings:

| Field | Value |
|-------|-------|
| Name | `mpsc-it-club` |
| Region | Singapore |
| Branch | `main` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn run_server:app` |

5. Click **"Advanced"** and add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SECRET_KEY`

6. Click **"Create Web Service"**

After ~3 minutes, you'll get a live URL:
```
https://mpsc-it-club.onrender.com
```

### 5.3 — Updating the Website

```bash
git add .
git commit -m "Describe your change"
git push
```

Render will automatically redeploy.

---

## Admin Panel Guide

Access at `/admin` (must be logged in as admin).

| Section | What you can do |
|---------|----------------|
| EC Panel | Add, remove, manage executive committee members |
| Events | Create and manage club events |
| Programs | Add past programs and workshops |
| Gallery | Upload photos |
| Users | View registered members, change roles |
| Payments | Approve/reject registrations, download CSV |
| Password Reset | Generate reset links for members |

### Adding an EC Member

1. Go to Admin → EC Panel
2. Select the year (e.g. 2026)
3. Click **"Add EC Member"**
4. Fill in:
   - Year (e.g. `2026`)
   - Full Name
   - Designation (President, VP, Secretary, etc.)
   - Section (BVB / BVG / EVB / EVG)
   - Photo (upload the member's photo)
   - Social links — Facebook, Instagram, WhatsApp, Website (all optional)
   - Display Order (1 = shown first, 99 = shown last)
5. Click **"Save Member"**

---

## EC Member QR Codes

### How to Generate and Download

1. Go to Admin → EC Panel
2. Select the correct year
3. Click on the **member's name** (shown in green with a link icon)
4. A popup appears with a QR code
5. Click **"Download QR"** to save as PNG

### What the QR Code Does

Scanning the QR opens a digital ID card showing:
- Member photo
- Name and designation
- Section
- Mobile number (if entered)
- Social media links

### Printing on ID Cards

1. Download the QR PNG from admin panel
2. Insert it into your ID card design (Canva, Photoshop, or Word)
3. Print the ID cards
4. Scanning the QR opens the member's digital card on any phone

---

## Adding Content

### Club Information (About Page)
File: `backend/templates/about.html`
Open in any text editor and edit the HTML text content.

### Moderator Photo
In `about.html`, find the `<img src="...">` under "Faculty Guidance" and replace the URL.

### Navigation Links
File: `backend/templates/components/navbar.html`

### Footer
File: `backend/templates/components/footer.html`

---

## Troubleshooting

### Website won't start — ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Website won't start — SUPABASE_URL not found
- Make sure `.env` file exists in the root folder
- Check variable names have no spaces around `=`

### Cannot log into admin panel
- Go to Supabase → Table Editor → users
- Find your account row
- Change `role` from `member` to `admin`

### Images not loading
- Check the storage bucket is named exactly `mpsc-it-club`
- Check the bucket is set to Public
- Check storage policies allow public SELECT

### QR code not working
- The QR links to `/member/<member_id>` on your live domain
- When testing locally, the QR points to localhost which only works on your own computer
- Deploy to Render first, then generate and print QR codes

### Site is slow on first load (Render free tier)
This is normal. The free plan puts sites to sleep after 15 minutes of no traffic.
The first visitor after inactivity waits ~30 seconds for it to wake up.

---

## Important Notes

- Keep `.env` private. It contains secret keys that give full access to the database.
- Supabase free plan: 500MB database, 1GB storage, 2GB bandwidth per month.
- Render free plan: 750 hours/month of compute. Site sleeps after 15 minutes idle.
- Always generate and download QR codes AFTER deploying to Render, not locally.

---

*Guide prepared for MPSC IT Club — Mohammadpur Preparatory School and College.*

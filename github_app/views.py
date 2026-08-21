import requests
import json
import os
from datetime import datetime, timedelta, timezone
from django.shortcuts import render
from django.conf import settings
from .models import LeaderboardEntry, ScoreHistory


def fetch_github_data(username):
    github_token = getattr(settings, 'GITHUB_TOKEN', None) or os.environ.get('GITHUB_TOKEN', '')
    headers = {'Authorization': f'token {github_token}', 'Accept': 'application/vnd.github.mercy-preview+json'} if github_token else {'Accept': 'application/vnd.github.mercy-preview+json'}

    user_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
    events_url = f"https://api.github.com/users/{username}/events?per_page=100"

    user_response = requests.get(user_url, headers=headers)
    repos_response = requests.get(repos_url, headers=headers)
    events_response = requests.get(events_url, headers=headers)

    if user_response.status_code != 200 or repos_response.status_code != 200:
        return None

    user_data = user_response.json()
    repos = repos_response.json()
    events = events_response.json() if events_response.status_code == 200 else []

    if not isinstance(repos, list) or 'message' in user_data:
        return None

    total_stars = sum(r['stargazers_count'] for r in repos)
    total_repos = len(repos)
    original_repos = sum(1 for r in repos if not r['fork'])
    forked_repos = sum(1 for r in repos if r['fork'])
    languages = list(set(r['language'] for r in repos if r['language']))
    repos_with_desc = sum(1 for r in repos if r['description'])
    top_repos = sorted(repos, key=lambda r: r['stargazers_count'], reverse=True)[:3]
    all_repos = sorted(repos, key=lambda r: r['updated_at'], reverse=True)

    language_counts = {}
    for repo in repos:
        if repo['language']:
            language_counts[repo['language']] = language_counts.get(repo['language'], 0) + 1

    # Account age
    created_at = user_data.get('created_at', '')
    account_age = ''
    account_years = 0
    if created_at:
        created_date = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        days = (datetime.now() - created_date).days
        account_years = days // 365
        account_months = (days % 365) // 30
        account_age = f"{account_years}y {account_months}m" if account_years > 0 else f"{account_months} months"

    # Events analysis
    recent_commits, streak, monthly_activity = analyze_events(events)

    # Activity status
    if recent_commits >= 30:
        activity_status, activity_color, activity_icon = "Very Active", "#238636", "🔥"
    elif recent_commits >= 10:
        activity_status, activity_color, activity_icon = "Active", "#2ea043", "⚡"
    elif recent_commits >= 1:
        activity_status, activity_color, activity_icon = "Moderate", "#fd7e14", "📝"
    else:
        activity_status, activity_color, activity_icon = "Inactive", "#6c757d", "😴"

    # Profile completeness
    completeness_items = [
        ('Avatar', bool(user_data.get('avatar_url'))),
        ('Name', bool(user_data.get('name'))),
        ('Bio', bool(user_data.get('bio'))),
        ('Location', bool(user_data.get('location'))),
        ('Website', bool(user_data.get('blog'))),
        ('Company', bool(user_data.get('company'))),
    ]
    completeness_score = sum(1 for _, v in completeness_items if v)
    completeness_percent = int((completeness_score / len(completeness_items)) * 100)

    # Tech Stack
    tech_stack = detect_tech_stack(repos, languages)

    # Repository Quality
    quality_data = calculate_repo_quality(repos)

    # FIXED Score Formula
    score = 0
    score += min(original_repos * 5, 50)
    score += min(total_stars * 10, 50)
    score += min(len(languages) * 10, 30)
    score += min(repos_with_desc * 3, 20)
    score += min(account_years * 5, 15)
    score += min(recent_commits, 10)
    score += int(completeness_percent / 10)
    score += min(int(quality_data['avg_quality'] * 15), 15)
    score = min(score, 200)

    if score <= 50:
        rank, rank_icon, rank_color = "Beginner", "🌱", "#6c757d"
    elif score <= 100:
        rank, rank_icon, rank_color = "Rising Developer", "⚡", "#0dcaf0"
    elif score <= 150:
        rank, rank_icon, rank_color = "Skilled Developer", "🔥", "#fd7e14"
    else:
        rank, rank_icon, rank_color = "Expert Developer", "🚀", "#198754"

    # Personalized tips
    tips = generate_tips(user_data, repos, original_repos, forked_repos, repos_with_desc, recent_commits, languages, total_stars)

    # Score History
    score_history = []
    try:
        LeaderboardEntry.objects.update_or_create(
            username=username,
            defaults={
                'name': user_data.get('name', username),
                'avatar': user_data.get('avatar_url', ''),
                'score': score,
                'rank': rank,
                'rank_icon': rank_icon,
                'total_repos': total_repos,
                'total_stars': total_stars,
            }
        )
        ScoreHistory.objects.create(username=username, score=score)
        history = ScoreHistory.objects.filter(username=username).order_by('-recorded_at')[:7]
        score_history = [{'score': h.score, 'date': h.recorded_at.strftime('%b %d')} for h in reversed(history)]
    except:
        pass

    return {
        'username': username,
        'name': user_data.get('name', username),
        'bio': user_data.get('bio', ''),
        'avatar': user_data.get('avatar_url', ''),
        'location': user_data.get('location', ''),
        'website': user_data.get('blog', ''),
        'account_age': account_age,
        'total_repos': total_repos,
        'original_repos': original_repos,
        'forked_repos': forked_repos,
        'total_stars': total_stars,
        'languages': languages,
        'repos_with_desc': repos_with_desc,
        'score': score,
        'score_percent': (score / 200) * 100,
        'rank': rank,
        'rank_icon': rank_icon,
        'rank_color': rank_color,
        'top_repos': top_repos,
        'all_repos': all_repos,
        'language_counts': json.dumps(language_counts),
        'tips': tips,
        'recent_commits': recent_commits,
        'activity_status': activity_status,
        'activity_color': activity_color,
        'activity_icon': activity_icon,
        'completeness_items': completeness_items,
        'completeness_percent': completeness_percent,
        'tech_stack': tech_stack,
        'quality_data': quality_data,
        'streak': streak,
        'monthly_activity': json.dumps(monthly_activity),
        'score_history': json.dumps(score_history),
        'error': False,
    }


def detect_tech_stack(repos, languages):
    detected = list(languages)
    keywords = {
        'Django': ['django'],
        'Flask': ['flask'],
        'FastAPI': ['fastapi'],
        'React': ['react'],
        'Next.js': ['nextjs', 'next-js'],
        'Vue.js': ['vue'],
        'Node.js': ['nodejs', 'express'],
        'MongoDB': ['mongodb', 'mongo'],
        'PostgreSQL': ['postgresql', 'postgres'],
        'Docker': ['docker'],
        'Machine Learning': ['ml-', 'machine-learning'],
        'REST API': ['rest-api', 'restapi'],
        'Flutter': ['flutter'],
        'TensorFlow': ['tensorflow'],
    }
    for repo in repos:
        name = (repo.get('name', '') or '').lower()
        desc = (repo.get('description', '') or '').lower()
        topics = [t.lower() for t in repo.get('topics', [])]
        for tech, kws in keywords.items():
            if tech not in detected:
                for kw in kws:
                    if kw in name or kw in desc or kw in ' '.join(topics):
                        detected.append(tech)
                        break
    return detected[:12]


def calculate_repo_quality(repos):
    if not repos:
        return {'avg_quality': 0, 'quality_repos': 0, 'total_repos': 0, 'quality_percent': 0}
    original = [r for r in repos if not r.get('fork')]
    quality_count = 0
    for repo in original:
        pts = 0
        if repo.get('description'): pts += 1
        if repo.get('license'): pts += 1
        if repo.get('topics'): pts += 1
        if pts >= 2:
            quality_count += 1
    total = len(original)
    avg = quality_count / total if total > 0 else 0
    return {
        'avg_quality': avg,
        'quality_repos': quality_count,
        'total_repos': total,
        'quality_percent': int(avg * 100)
    }


def analyze_events(events):
    if not isinstance(events, list) or len(events) == 0:
        return 0, 0, {}

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_commits = 0
    commit_dates = set()

    monthly_activity = {}
    for i in range(5, -1, -1):
        month = datetime.now(timezone.utc) - timedelta(days=30 * i)
        monthly_activity[month.strftime('%b')] = 0

    for event in events:
        if event.get('type') != 'PushEvent':
            continue
        try:
            created_at = event.get('created_at', '')
            if not created_at:
                continue

            event_date = datetime.strptime(
                created_at, '%Y-%m-%dT%H:%M:%SZ'
            ).replace(tzinfo=timezone.utc)

            payload = event.get('payload', {})
            commits_list = payload.get('commits', [])
            size = payload.get('size', 0)
            commits_count = max(len(commits_list), size, 1)

            if event_date > thirty_days_ago:
                recent_commits += commits_count

            commit_dates.add(event_date.date())

            month_key = event_date.strftime('%b')
            if month_key in monthly_activity:
                monthly_activity[month_key] += commits_count

        except Exception as e:
            print(f"Event error: {e}")
            continue

    # Streak calculate karo
    streak = 0
    if commit_dates:
        today = datetime.now(timezone.utc).date()
        yesterday = today - timedelta(days=1)

        start = today if today in commit_dates else yesterday
        current = start
        while current in commit_dates:
            streak += 1
            current -= timedelta(days=1)

    return recent_commits, streak, monthly_activity


def generate_tips(user_data, repos, original_repos, forked_repos, repos_with_desc, recent_commits, languages, total_stars):
    tips = []
    if not user_data.get('bio'):
        tips.append("Add a bio — recruiters spend 10 seconds on your profile, bio is the first thing they read")
    if not user_data.get('blog'):
        tips.append("Add your LinkedIn or portfolio URL — 80% of recruiters check it before reaching out")
    if not user_data.get('location'):
        tips.append("Add your city — local recruiters filter by location when hiring")
    missing_desc = len([r for r in repos if not r.get('fork')]) - repos_with_desc
    if missing_desc > 0:
        tips.append(f"{missing_desc} repos have no description — add them to boost discoverability")
    if forked_repos > original_repos:
        tips.append("More forked repos than original — recruiters want to see what YOU built")
    if recent_commits < 5:
        tips.append("Low recent activity — consistent commits signal to hiring managers that you actively code")
    if len(languages) < 2:
        tips.append("Only one language detected — multi-language developers get 3x more recruiter messages")
    if total_stars == 0:
        tips.append("No stars yet — share your best project on LinkedIn to start getting stars")
    if original_repos < 3:
        tips.append("Build at least 3 strong original projects — portfolio matters more than your degree")
    if not tips:
        tips.append("Great profile! Pin your top 6 repos on GitHub so recruiters see your best work first")
        tips.append("Write a detailed README — treat it like a mini case study of your work")
    return tips[:4]


def home(request):
    return render(request, 'home.html')


def score_card(request):
    username = request.GET.get('username', '')
    data = {'error': False}
    if username:
        result = fetch_github_data(username)
        data = result if result else {'error': True, 'username': username}
    return render(request, 'score_card.html', data)


def leaderboard(request):
    entries = LeaderboardEntry.objects.all().order_by('-score')[:20]
    return render(request, 'leaderboard.html', {'entries': entries})
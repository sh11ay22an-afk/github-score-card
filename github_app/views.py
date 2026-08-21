import requests
import json
import os
from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import render
from .models import LeaderboardEntry


def fetch_github_data(username):
    user_url = f"https://api.github.com/users/{username}"
    repos_url = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=100"
    events_url = f"https://api.github.com/users/{username}/events?per_page=100"

    headers = {}
    github_token = getattr(settings, 'GITHUB_TOKEN', None)
    if github_token:
        headers = {'Authorization': f'token {github_token}'}

    user_response = requests.get(user_url, headers=headers)
    repos_response = requests.get(repos_url, headers=headers)

    if user_response.status_code != 200:
        return None
    if repos_response.status_code != 200:
        return None

    user_data = user_response.json()
    repos = repos_response.json()

    events = requests.get(events_url, headers=headers).json()

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

    created_at = user_data.get('created_at', '')
    account_age = ''
    account_years = 0
    if created_at:
        created_date = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%SZ')
        days = (datetime.now() - created_date).days
        account_years = days // 365
        account_months = (days % 365) // 30
        account_age = f"{account_years}y {account_months}m" if account_years > 0 else f"{account_months} months"

    recent_commits = 0
    if isinstance(events, list):
        thirty_days_ago = datetime.now() - timedelta(days=30)
        for event in events:
            if event.get('type') == 'PushEvent':
                try:
                    event_date = datetime.strptime(event['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if event_date > thirty_days_ago:
                        recent_commits += event.get('payload', {}).get('size', 0)
                except:
                    pass

    if recent_commits >= 30:
        activity_status, activity_color, activity_icon = "Very Active", "#238636", "🔥"
    elif recent_commits >= 10:
        activity_status, activity_color, activity_icon = "Active", "#2ea043", "⚡"
    elif recent_commits >= 1:
        activity_status, activity_color, activity_icon = "Moderate", "#fd7e14", "📝"
    else:
        activity_status, activity_color, activity_icon = "Inactive", "#6c757d", "😴"

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

    score = 0
    score += original_repos * 10
    score += total_stars * 5
    score += len(languages) * 15
    score += repos_with_desc * 10
    score += account_years * 5
    score += min(recent_commits, 10) * 2
    score += int(completeness_percent / 10) * 3
    score = min(score, 200)

    if score <= 50:
        rank, rank_icon, rank_color = "Beginner", "🌱", "#6c757d"
    elif score <= 100:
        rank, rank_icon, rank_color = "Rising Developer", "⚡", "#0dcaf0"
    elif score <= 150:
        rank, rank_icon, rank_color = "Skilled Developer", "🔥", "#fd7e14"
    else:
        rank, rank_icon, rank_color = "Expert Developer", "🚀", "#198754"

        # Career-focused personalized tips
    tips = []
    if not user_data.get('bio'):
        tips.append("Add a bio — recruiters spend 10 seconds on your profile, bio is the first thing they read")
    if not user_data.get('blog'):
        tips.append("Add your LinkedIn or portfolio URL — 80% of recruiters check it before reaching out")
    if not user_data.get('location'):
        tips.append("Add your city — local recruiters filter by location when hiring")
    missing_desc = total_repos - repos_with_desc
    if missing_desc > 0:
        tips.append(f"{missing_desc} repos have no description — repo descriptions appear in Google search results, add them for better discoverability")
    if forked_repos > original_repos:
        tips.append("You have more forked repos than original projects — recruiters want to see what YOU built, not what you copied")
    if recent_commits < 5:
        tips.append("Low recent activity — consistent commits signal to hiring managers that you actively code, even small pushes help")
    if len(languages) < 2:
        tips.append("Only one language detected — multi-language developers get 3x more recruiter messages on LinkedIn")
    if total_stars == 0:
        tips.append("No stars yet — share your best project on LinkedIn with a proper post, stars build social proof")
    if original_repos < 3:
        tips.append("Build at least 3 strong original projects — quality portfolio projects matter more than your degree to most startups")
    if not tips:
        tips.append("Strong profile! Pin your top 6 repos on GitHub to make sure recruiters see your best work first")
        tips.append("Write a detailed README for each project — treat it like a mini case study showing problem, solution, and tech stack")
    tips = tips[:4]

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
        'error': False,
    }


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

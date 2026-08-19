import requests

USERNAME = "sh11ay22an-afk"

# User data
user_url = f"https://api.github.com/users/{USERNAME}"
user_data = requests.get(user_url).json()

# Repos data
repos_url = f"https://api.github.com/users/{USERNAME}/repos"
repos = requests.get(repos_url).json()

# Score Calculate Karo
total_stars = sum(r['stargazers_count'] for r in repos)
total_repos = len(repos)
languages = set(r['language'] for r in repos if r['language'])
repos_with_desc = sum(1 for r in repos if r['description'])

score = 0
score += total_repos * 10        # Har repo = 10 points
score += total_stars * 5         # Har star = 5 points
score += len(languages) * 15     # Har language = 15 points
score += repos_with_desc * 10    # Description wale = 10 points

print("=" * 40)
print(f"  GitHub Score Card — {USERNAME}")
print("=" * 40)
print(f"Total Repos     : {total_repos}")
print(f"Total Stars     : {total_stars}")
print(f"Languages Used  : {', '.join(languages)}")
print(f"Repos w/ Desc   : {repos_with_desc}/{total_repos}")
print("=" * 40)
print(f"  DEVELOPER SCORE : {score} / 200")
print("=" * 40)
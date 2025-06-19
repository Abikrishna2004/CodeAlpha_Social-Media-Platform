from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta

from .models import Post, Comment, Like, Follow, Message, Story
from .forms import PostForm

# HOME: Feed showing followed users + own posts
@login_required
def home(request):
    following_users = Follow.objects.filter(follower=request.user).values_list('following', flat=True)
    posts = Post.objects.filter(author__in=following_users).union(
        Post.objects.filter(author=request.user)
    ).order_by('-timestamp')
    return render(request, 'core/home.html', {'posts': posts})

# EXPLORE: Show all posts publicly
def explore(request):
    posts = Post.objects.all().order_by('-timestamp')
    return render(request, 'core/explore.html', {'posts': posts})

# PROFILE: View user profile
def profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=profile_user)
    is_following = False

    if request.user.is_authenticated:
        is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()

    followers_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()

    return render(request, 'core/profile.html', {
        'profile_user': profile_user,
        'posts': posts,
        'is_following': is_following,
        'followers_count': followers_count,
        'following_count': following_count
    })

# TOGGLE FOLLOW
@login_required
def follow_user(request, username):
    target_user = get_object_or_404(User, username=username)
    if request.user != target_user:
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)
        if not created:
            follow.delete()
    return redirect('profile', username=username)

# REGISTER
def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'core/register.html', {'form': form})

# CREATE POST
@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('home')
    else:
        form = PostForm()
    return render(request, 'core/create_post.html', {'form': form})

# LIKE / UNLIKE POST
@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)
    if not created:
        like.delete()
    return HttpResponseRedirect(reverse('home'))

# COMMENT ON POST
@require_POST
@login_required
def comment_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    text = request.POST.get("text")
    if text:
        Comment.objects.create(post=post, user=request.user, text=text)
    return redirect('home')

# SEARCH USERS
def search(request):
    query = request.GET.get('q')
    results = User.objects.filter(Q(username__icontains=query)) if query else []
    return render(request, 'core/search_results.html', {'query': query, 'results': results})

# INBOX
@login_required
def inbox(request):
    users = User.objects.exclude(id=request.user.id)
    return render(request, 'core/inbox.html', {'users': users})

# CHAT BETWEEN USERS
@login_required
def chat(request, username):
    other_user = get_object_or_404(User, username=username)
    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=request.user, receiver=other_user, content=content)

    return render(request, 'core/chat.html', {'messages': messages, 'other_user': other_user})

# STORIES - 24hr FEED
@login_required
def story_list(request):
    stories = Story.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).order_by('-created_at')
    return render(request, 'core/stories.html', {'stories': stories})

import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Room, Topic, Message, User, News, Bookmark
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import RoomForm, UserForm, MyUserCreationForm


# Create your views here.

# rooms = [
#     {'id': 1, 'name': 'lagi belajar python'},
#     {'id': 2, 'name': 'akbar bintang'},
#     {'id': 3, 'name': 'akbar bintang wicaksono'},
# ]


def loginPage(request):
    page = 'login'
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username').lower()
        password = request.POST.get('password')
        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, 'User does not exist')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Username or password does not exist')
    context = {'page': page}
    return render(request, 'base/login_register.html', context)


def logoutUser(request):
    logout(request)
    return redirect('home')


def registerPage(request):
    form = MyUserCreationForm()

    if request.method == 'POST':
        form = MyUserCreationForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            user.save()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'An error accured during registration')
    return render(request, 'base/login_register.html', {'form': form})


def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''
    rooms = Room.objects.filter(
        Q(topic__name__icontains=q) |
        Q(name__icontains=q) |
        Q(description__icontains=q)
    )
    topics = Topic.objects.all()[0:5]
    room_count = rooms.count()
    room_messages = Message.objects.filter(Q(room__topic__name__icontains=q))
    context = {'rooms': rooms, 'topics': topics, 'room_count': room_count, 'room_messages': room_messages}
    return render(request, 'base/pages/home/home.html', context)


def room(request, pk):
    room = Room.objects.get(id=pk)
    room_messages = room.message_set.all()
    participants = room.participants.all()
    cek_bookmark = Bookmark.objects.filter(room=room, user=request.user).exists()
    if request.method == 'POST':
        message = Message.objects.create(
            user=request.user,
            room=room,
            body=request.POST.get('body')
        )
        room.participants.add(request.user)
        return redirect('room', pk=room.id)
    context = {'room': room, 'room_messages': room_messages, 'participants': participants,'cek_bookmark':cek_bookmark}
    return render(request, 'base/pages/room/room.html', context)

def news(request):
    search = request.GET.get('search')
    response = requests.get(
        "https://newsapi.org/v2/top-headlines?country=us&apiKey=32688567304b4ed78403e4d6030ede04")
    data = response.json()
    print(data)
    for item in data['articles']:
        cek_news = News.objects.filter(title=item['title']).exists()
        if cek_news == False:
            News.objects.create(
                title=item['title'],
                description=item['description'],
                url=item['url'],
                urlToImage=item['urlToImage'])
        else:
            News.objects.filter(title=item['title']).update(title=item['title'], description=item['description'], url=item['url'],
                        urlToImage=item['urlToImage'])

    if search:
        data = News.objects.filter(title__icontains=search)
    else:
        data = News.objects.all()
    # Simpan data ke dalam model Django

    return render(request, 'base/pages/news/news.html', {'data': data})

def userProfile(request, pk):
    user = User.objects.get(id=pk)
    rooms = user.room_set.all()
    room_messages = user.message_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'rooms': rooms, 'topics': topics, 'room_messages': room_messages}
    return render(request, 'base/pages/profile/profile.html', context)


@login_required(login_url='/login')
def createRoom(request):
    form = RoomForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)

        Room.objects.create(
            host=request.user,
            topic=topic,
            name=request.POST.get('name'),
            description=request.POST.get('description'),
        )

        return redirect('home')

    context = {'form': form, 'topics': topics}
    return render(request, 'base/pages/room/room_form.html', context)


@login_required(login_url='/login')
def updateRoom(request, pk):
    room = Room.objects.get(id=pk)
    form = RoomForm(instance=room)
    topics = Topic.objects.all()
    if request.user != room.host:
        return HttpResponse('your are not allowed here!')
    if request.method == 'POST':
        topic_name = request.POST.get('topic')
        topic, created = Topic.objects.get_or_create(name=topic_name)
        room.name = request.POST.get('name')
        room.topic = topic
        room.description = request.POST.get('description')
        room.save()
        return redirect('home')
    context = {'form': form, 'topics': topics, 'room':room}
    return render(request, 'base/pages/room/room_form.html', context)


@login_required(login_url='/login')
def deleteRoom(request, pk):
    room = Room.objects.get(id=pk)
    if request.user != room.host:
        return HttpResponse('your are not allowed here!')
    if request.method == 'POST':
        room.delete()
        return redirect('home')
    return render(request, 'base/delete.html', {'obj': room})


@login_required(login_url='/login')
def deleteMessage(request, pk):
    message = Message.objects.get(id=pk)
    if request.user != message.user:
        return HttpResponse('your are not allowed here!')
    if request.method == 'POST':
        message.delete()
        return redirect('home')

    return render(request, 'base/delete.html', {'obj': message})

@login_required(login_url='/login')
def updateUser(request, pk):
    user = request.user
    form = UserForm(instance=user)

    if request.method == 'POST':
        form = UserForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            return redirect('user-profile', pk=user.id)
    return render(request, 'base/pages/profile/update-user.html',  {'form': form})


@login_required(login_url='/login')
def bookmark(request, pk):
    print(f'Request method: {request.method}')  # Debug line
    # print(f'Primary key: {pk}')
    if request.method == 'POST':
        user = request.user
        if request.POST.get('bookmarking'):
            bookmark = Bookmark(user=user, room_id=request.POST.get('bookmarking'))
            bookmark.save()
            messages.success(request, 'Bookmarked!')
            return redirect('bookmarked_items')
    return redirect('home')

def bookmarked_items(request):
    user = request.user
    bookmarked_rooms = Bookmark.objects.filter(user=user, room__isnull=False)
    bookmarked_news = Bookmark.objects.filter(user=user, news__isnull=False)
    context = {
        'bookmarked_rooms': bookmarked_rooms,
        'bookmarked_news': bookmarked_news,
    }
    return render(request, 'base/pages/bookmarked_items.html', context)
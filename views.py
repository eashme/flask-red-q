from django.http import HttpResponse

def index(request):
    	if request.method == 'GET'
		return HttpResponse("please go to login")
	elif request.method == "POST":
		return HttpResponse("please get there next time")

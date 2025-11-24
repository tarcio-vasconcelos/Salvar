from django.shortcuts import render

# Create your views here.
def laws_list(request):
    return render(request, 'laws/laws.html')
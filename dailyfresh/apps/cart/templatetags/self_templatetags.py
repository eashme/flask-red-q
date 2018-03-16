from django.template import Library

register = Library()

@register.filter
def account_two(num1,num2):
    return int(num1) * num2
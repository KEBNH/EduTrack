from django.contrib import admin
from django.urls import path
from .views import EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView, inicio

urlpatterns = [
    path('', inicio),
    path('employee/', EmployeeListView.as_view(), name='employee_list'),
    path('employee-create/', EmployeeCreateView.as_view(), name='employee_create'),
    path('employee-edit/<str:codigo_unico>', EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employee-delete/<str:codigo_unico>', EmployeeDeleteView.as_view(), name='employee_delete'),
]
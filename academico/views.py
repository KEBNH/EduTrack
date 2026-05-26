from django.shortcuts import render, get_object_or_404
from django.views.generic import (ListView, CreateView, UpdateView, DeleteView, DetailView)
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
#from accounts.mixins import RolRequiredMixin
from .models import Employee
from .forms import EmployeeForm

def inicio(request):
    return render (request, 'bashboard.html')

#===============================================
#====== VIEW DEL MODELO Employee
#===============================================
#class EmployeeListView(LoginRequiredMixin, RolRequiredMixin, ListView):
class EmployeeListView(ListView):
    model = Employee
    template_name = 'employee.html'
    context_object_name = 'employees'
    paginate_by = 1
    #roles_permitidos = ["ADMIN", "COORDINADOR"]

    #Código para Filtro y Paginación
    def get_queryset(self):
        queryset = Employee.objects.only('id', 'codigo_unico', 'dni', 'nombre', 'apellidos', 'celular', 'correo', 'rol', 'activo').order_by('apellidos')
        
        filtro = self.request.GET.get('q', '').strip()
        print(filtro)
        if filtro:
            queryset = queryset.filter(
                Q(dni__icontains=filtro) |
                Q(nombre__icontains=filtro) |
                Q(apellidos__icontains=filtro)
            )
        return queryset
    
    def get_context_data(self, **kwargs): # Se usa para mantener el filtro al paginar        
        context = super().get_context_data(**kwargs)
        paginator = context['paginator']
        page_obj = context['page_obj']

        context.update({
            'page_range': self._get_page_range(paginator.num_pages, page_obj.number, window=4),
            'q': self.request.GET.get('q', ''),
        })
        return context
    
    def _get_page_range(self, total_pages, current_page, window=4): #Retorna un rango de páginas centrado en la página actual
        start = max(current_page - window, 1)
        end = min(current_page + window + 1, total_pages)
        return range(start, end + 1)

#class EmployeeCreateView(LoginRequiredMixin, CreateView):
class EmployeeCreateView(CreateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee_form.html'
    success_url = reverse_lazy('employee_list')

class EmployeeUpdateView(UpdateView):
    model = Employee
    form_class = EmployeeForm
    template_name = 'employee_form.html'
    success_url = reverse_lazy('employee_list')

    def get_object(self):
        return get_object_or_404(
            Employee,
            codigo_unico=self.kwargs['codigo_unico']
        )

class EmployeeDeleteView(LoginRequiredMixin, DeleteView):
    model = Employee
    template_name = 'employee/confirm_delete.html'
    success_url = reverse_lazy('employee_list')

    def get_object(self):
        return get_object_or_404(
            Employee,
            codigo_unico=self.kwargs['codigo_unico']
        )
    

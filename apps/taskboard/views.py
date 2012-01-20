from django.views.generic import CreateView, UpdateView, ListView, DetailView

from funfactory.urlresolvers import reverse
from taskboard.forms import TaskForm
from taskboard.models import Task


class CreateTask(CreateView):
    form_class = TaskForm
    template_name = "taskboard/edit_task.html"
    model = Task

    def get_success_url(self):
        # had to do this instead of just defining success_url because of some
        # loading order issue that would break urls.
        return reverse('taskboard_task_list')


class EditTask(UpdateView):
    form_class = TaskForm
    template_name = "taskboard/edit_task.html"
    model = Task
    context_object_name = "task"

    def get_success_url(self):
        return reverse('taskboard_task_detail', kwargs={'pk':self.object.pk})


class ViewTask(DetailView):
    model = Task
    template_name = "taskboard/list_tasks.html"


class ListTasks(ListView):
    queryset = Task.objects.filter(disabled=False)
    template_name = "taskboard/list_tasks.html"

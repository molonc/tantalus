from django.views.generic.list import ListView
from django.views.generic.edit import CreateView
from django.views.generic.edit import ModelFormMixin
from tantalus.models import Transfer
from tantalus.tasks import run_transfer


class TransferListView(ListView):
    model = Transfer


class TransferCreate(CreateView):
    model = Transfer
    fields = ['name']

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            self.object = form.save()
            self.object.state = 'Started'
            self.object.save()
            run_transfer.delay(self.object.id)
            return super(ModelFormMixin, self).form_valid(form)
        else:
            return self.form_invalid(form)



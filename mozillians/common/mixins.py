from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.module_loading import import_string

import boto

from boto.s3.connection import OrdinaryCallingFormat
from celery.task import task
from import_export.admin import ExportMixin
from import_export.forms import ExportForm


ADMIN_EXPORT_TIMEOUT = 10 * 60


@task(soft_time_limit=ADMIN_EXPORT_TIMEOUT)
def async_data_export(file_format, values_list, qs_model, filename):
    """Task to export data from admin site and store it to S3."""

    from django.contrib import admin

    admin_obj = admin.site._registry[qs_model]
    queryset = qs_model.objects.filter(id__in=values_list)
    resource_class = admin_obj.get_export_resource_class()

    data = resource_class().export(queryset)
    export_data = file_format.export_data(data)

    # Store file to AWS S3
    kwargs = {
        'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
        'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
        # Required to avoid ssl issues when bucket contains dots
        'calling_format': OrdinaryCallingFormat()
    }
    conn = boto.connect_s3(**kwargs)
    bucket = conn.get_bucket(settings.MOZILLIANS_ADMIN_BUCKET)
    key = bucket.new_key(filename)
    key.set_contents_from_string(export_data)


class S3ExportMixin(ExportMixin):

    def get_export_filename(self, file_format):
        query_str = self.request.GET.urlencode().replace('=', '_')
        if query_str == '':
            query_str = 'All'
        date_str = datetime.now().strftime('%Y-%m-%d-%H:%m:%s')
        filename = '{model}-{filter}-{date}.{extension}'.format(
            model=self.model.__name__, filter=query_str, date=date_str,
            extension=file_format.get_extension())
        return filename

    def get_export_data(self, file_format, queryset):
        """Returns the id from the celery task spawned to export data to S3."""

        kwargs = {
            'file_format': file_format,
            'values_list': list(queryset.values_list('id', flat=True)),
            'qs_model': queryset.model,
            'filename': self.get_export_filename(file_format)
        }

        return async_data_export.delay(**kwargs)

    def export_action(self, request, *args, **kwargs):
        self.request = request
        formats = self.get_export_formats()
        form = ExportForm(formats, request.POST or None)

        if form.is_valid():
            file_format = formats[int(form.cleaned_data['file_format'])]()
            queryset = self.get_export_queryset(request)
            task_id = self.get_export_data(file_format, queryset)
            filename = self.get_export_filename(file_format)
            msg = 'Data export task spawned with id: {} and filename: {}'.format(task_id, filename)
            messages.info(request, msg)
            return redirect('admin:index')

        context = {}
        context.update(self.admin_site.each_context(request))

        context['form'] = form
        context['opts'] = self.model._meta
        request.current_app = self.admin_site.name
        return TemplateResponse(request, [self.export_template_name], context)


# Allow configuring admin export mixin in project settings in case we need to fallback to default
MozilliansAdminExportMixin = import_string(settings.ADMIN_EXPORT_MIXIN)

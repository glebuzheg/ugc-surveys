from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms.models import BaseInlineFormSet
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Choice, Question, Survey
from .utils.statistics import survey_statistics


class OrderedInlineForm(forms.ModelForm):
    def _get_validation_exclusions(self):
        # Validate positions together: each intermediate row in a swap may collide.
        return super()._get_validation_exclusions() | {"position"}


class OrderedInlineFormSet(BaseInlineFormSet):
    @transaction.atomic
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        survey_id = (
            self.instance.pk if isinstance(self.instance, Survey) else self.instance.survey_id
        )
        if survey_id:
            Survey.objects.select_for_update().get(pk=survey_id)
        positions = dict(self.get_queryset().values_list("pk", "position"))
        active = []
        for form in self.forms:
            if not form.cleaned_data:
                continue
            positions.pop(form.instance.pk, None)
            if not form.cleaned_data.get("DELETE"):
                active.append(form)
        explicit = list(positions.values()) + [
            form.cleaned_data["position"]
            for form in active
            if form.cleaned_data.get("position") is not None
        ]
        if len(explicit) != len(set(explicit)):
            raise ValidationError("Позиции должны быть уникальными в пределах родителя.")
        last = max(explicit, default=0)
        for form in active:
            if form.cleaned_data.get("position") is None:
                last += 1
                form.instance.position = last


class QuestionInline(admin.TabularInline):
    model = Question
    form = OrderedInlineForm
    formset = OrderedInlineFormSet
    fields = ("text", "position", "allow_custom_answer")
    extra = 1
    show_change_link = True


class ChoiceInline(admin.TabularInline):
    model = Choice
    form = OrderedInlineForm
    formset = OrderedInlineFormSet
    fields = ("text", "position")
    extra = 1


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "is_published", "created_at", "statistics_link")
    list_filter = ("is_published",)
    search_fields = ("title",)
    raw_id_fields = ("author",)
    readonly_fields = ("created_at", "statistics_link")
    list_select_related = ("author",)
    inlines = (QuestionInline,)
    actions = None  # Individual deletion uses the model's transaction and PROTECT.

    @admin.display(description="Статистика")
    def statistics_link(self, obj):
        if not obj.pk:
            return "Сначала сохраните опрос."
        return format_html(
            '<a href="{}">Посмотреть статистику</a>',
            reverse(
                "admin:surveys_survey_statistics",
                args=[obj.pk],
            ),
        )

    def get_urls(self):
        return [
            path(
                "<int:object_id>/statistics/",
                self.admin_site.admin_view(self.statistics_view),
                name="surveys_survey_statistics",
            ),
            *super().get_urls(),
        ]

    def statistics_view(self, request, object_id):
        survey = self.get_object(request, str(object_id))
        if survey is None or not self.has_view_permission(request, survey):
            raise PermissionDenied
        return TemplateResponse(
            request,
            "admin/surveys/statistics.html",
            {
                **self.admin_site.each_context(request),
                "title": f"Статистика: {survey}",
                "statistics": survey_statistics(survey),
                "opts": self.model._meta,
            },
        )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "survey", "position", "allow_custom_answer")
    list_select_related = ("survey",)
    search_fields = ("text",)
    raw_id_fields = ("survey",)
    inlines = (ChoiceInline,)
    actions = None

    def get_readonly_fields(self, request, obj=None):
        return ("survey",) if obj else ()

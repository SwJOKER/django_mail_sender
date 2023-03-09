from django.conf.urls import url

import views

handler404 = 'mailtasks.views.view_404'

urlpatterns = [
    url(r'^smtp/?$', views.CreateSmtpView.as_view(), name='set_smtp'),
    url(r'^delivery/(?P<uuid>[0-9a-f-]+)/?$', views.TrackMessageView.as_view(), name='delivery_link'),
    url(r'^tasks/new_task/check/?$', views.CheckTemplateView.as_view(), name='check_template'),
    url(r'^tasks/new_task/?$', views.CreateTaskView.as_view(), name='new_task'),
    url(r'^tasks/(?P<pk>\d+)/stop/?$', views.TaskStopView.as_view(), name='task_stop'),
    url(r'^tasks/(?P<pk>\d+)/delete/?$', views.TaskDeleteView.as_view(), name='task_delete'),
    url(r'^tasks/(?P<pk>\d+)/?$', views.TaskDetailView.as_view(), name='task_detail'),
    url(r'^tasks/?$', views.TaskListView.as_view(), name='task_list'),
    url(r'^subscribers/new_list/?$', views.SubscribersListCreateView.as_view(), name='new_subscribers'),
    url(r'^subscribers/variables/?$', views.SubscribersVarsJsonView.as_view(), name='subscribers_variables'),
    url(r'^subscribers/(?P<pk>\d+)/delete/?$', views.SubscribersListDeleteView.as_view(), name='subscribers_list_delete'),
    url(r'^subscribers/(?P<pk>\d+)/variables/?$', views.EditSubsListVarsView.as_view(), name='subscribers_edit_vars'),
    url(r'^letters/(?P<pk>[0-9a-f-]+)/?$', views.LetterDetailView.as_view(), name='letter_detail'),
    url(r'^subscribers/(?P<pk>\d+)/?$', views.SubscribersListDetailView.as_view(), name='subscribers_list_detail'),
    url(r'^subscribers/?$', views.SubscribersListsView.as_view(), name='subscribers'),
    url(r'^templates/(?P<pk>\d+)/delete/?$', views.TemplateDeleteView.as_view(), name='template_delete'),
    url(r'^templates/(?P<pk>\d+)/?$', views.TemplateDetailView.as_view(), name='template_detail'),
    url(r'^templates/new_template/?$', views.CreateTemplateView.as_view(), name='new_template'),
    url(r'^templates/?$', views.TemplatesView.as_view(), name='templates'),
    url(r'^login/?$', views.post_login, name='post_login'),
    url(r'^reset/?$', views.PasswordReset.as_view(), name='reset_password'),
    url(r'^registration/?$', views.RegisterView.as_view(), name='registration'),
    url(r'^$', views.IndexView.as_view(), name='index'),
]

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from magiclink.models import MagicLink

User = get_user_model()


@pytest.mark.django_db
def test_signup_end_to_end(mocker, settings, client):
    spy = mocker.spy(MagicLink, 'get_magic_link_url')

    login_url = reverse('magiclink:signup')
    email = 'test@example.com'
    first_name = 'test'
    last_name = 'name'
    data = {
        'form_name': 'SignupForm',
        'email': email,
        'name': f'{first_name} {last_name}',
    }
    client.post(login_url, data, follow=True)
    verify_url = spy.spy_return
    response = client.get(verify_url, follow=True)
    assert response.status_code == 200
    assert response.request['PATH_INFO'] == reverse('needs_login')
    assert response.context['user'].email == email
    assert response.context['user'].first_name == first_name
    assert response.context['user'].last_name == last_name

    url = reverse('magiclink:logout')
    response = client.get(url, follow=True)
    assert response.status_code == 200
    assert response.request['PATH_INFO'] == reverse('empty')

    url = reverse('needs_login')
    response = client.get(url, follow=True)
    assert response.status_code == 200
    assert response.request['PATH_INFO'] == reverse('magiclink:login')


def test_signup_get(client):
    url = reverse('magiclink:signup')
    response = client.get(url)
    assert response.context_data['SignupForm']
    assert response.context_data['SignupFormEmailOnly']
    assert response.context_data['SignupFormWithUsername']
    assert response.context_data['SignupFormFull']
    assert response.status_code == 200


@pytest.mark.django_db
def test_signup_post(mocker, client, settings):  # NOQA: F811
    from magiclink import settings as mlsettings
    send_mail = mocker.patch('magiclink.models.send_mail')

    url = reverse('magiclink:signup')
    email = 'test@example.com'
    data = {
        'form_name': 'SignupForm',
        'email': email,
        'name': 'testname',
    }
    response = client.post(url, data)
    assert response.status_code == 302
    assert response.url == reverse('magiclink:login_sent')

    usr = User.objects.get(email=email)
    assert usr
    magiclink = MagicLink.objects.get(email=email)
    assert magiclink
    if settings.MAGICLINK_REQUIRE_BROWSER:
        assert response.cookies['magiclink'].value == magiclink.cookie_value

    send_mail.assert_called_once_with(
        subject=mlsettings.EMAIL_SUBJECT,
        message=mocker.ANY,
        recipient_list=[email],
        from_email=settings.DEFAULT_FROM_EMAIL,
        html_message=mocker.ANY,
    )


@pytest.mark.django_db
def test_login_signup_form_missing_name(mocker, client, settings):  # NOQA: F811, E501
    url = reverse('magiclink:signup')
    data = {
        'form_name': 'SignupForm',
        'email': 'test@example.com',
    }
    response = client.post(url, data)
    assert response.status_code == 200
    error = ['This field is required.']
    assert response.context_data['SignupForm'].errors['name'] == error

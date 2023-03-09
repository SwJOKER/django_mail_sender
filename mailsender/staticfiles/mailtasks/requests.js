"use strict";

window.addEventListener('load', (event) => {
    logout_button.addEventListener('click', logoutRequest)

    login_form.style.display = user_logged == 'False' ? 'grid' : 'none';
    logged_menu.style.display = user_logged == 'True' ? 'grid' : 'none';

    document.forms.login.addEventListener('submit', loginRequest)
    document.forms.reset.addEventListener('submit', ResetRequest)

    forgot_pwd_link.addEventListener('click', function(){
        login_form.style.display = 'none'
        reset_pwd_form.style.display = 'grid'
    })

    cancel_reset_button.addEventListener('click', function() {
        login_form.style.display = 'grid'
        reset_pwd_form.style.display = 'none'
    })

    document.forms.registration.addEventListener('submit', registration_request)

    create_account.addEventListener('click', function() {
        registration_form.style.display = 'grid'
        login_form.style.display = 'none'
    })

    cancel_registration_button.addEventListener('click', function(){
        registration_form.style.display = 'none'
        login_form.style.display = 'grid'
    })

    async function postQuery(url, data, credentials = false) {
        let response = await fetch(url, {
          method: 'POST',
          withCredentials: credentials,
          headers: {
            'X-CSRFToken': csrftoken,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(data)
        });
        return response
    }

    async function logoutRequest() {
        let url = '/logout/'
        let response = await fetch(url, {
            method: "POST",
            headers: {'X-CSRFToken': csrftoken},
        });
        location.reload()
    }

    async function ResetRequest(event) {
        event.preventDefault()
        let url = reset_url
        let form = document.forms.reset
        let data = {
            email: form.email.value
        }
        let response = await fetch(url, {
            method: "POST",
            body: JSON.stringify(data),
            withCredentials: true,
            headers: {
                'X-CSRFToken': csrftoken,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
        });
        if (response.status === 200) {
            let response_error_msg = await response.json()
            if ('error' in response_error_msg) {
                reset_pwd_msg.style.display = 'block'
                reset_pwd_msg.style.color = 'red'
                reset_pwd_msg.innerHTML = response_error_msg['error']
            } else {
                reset_pwd_msg.style.display  = 'block'
                reset_pwd_msg.style.color = '#8ac858'
                reset_pwd_msg.innerHTML = response_error_msg['msg']
            }
        }
    }



    async function loginRequest(event) {
        event.preventDefault()
        let url = login_url
        let form = document.forms.login
        let data = {
            username: form.username.value,
            password: form.password.value,
        }
        let response = await fetch(url, {
            method: "POST",
            body: JSON.stringify(data),
            withCredentials: true,
            headers: {
                'X-CSRFToken': csrftoken,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
        });
        if (response.status === 200) {
            let response_error_msg = await response.json()
            if ('error' in response_error_msg) {
                login_error_msg.innerHTML = response_error_msg['error']
                form.password.value = ''
            } else {
                logged_menu.style.display = 'grid'
                login_form.style.display = 'none'
                location.reload()
            }
        }
    }

    async function registration_request(event) {
        event.preventDefault()
        passwrod_registration_msg.style.display = 'none'
        name_registration_msg.style.display = 'none'
        email_registration_msg.style.display = 'none'
        let url = registration_url
        let form = document.forms.registration
        let data = {
            username: form.login.value,
            password1: form.password1.value,
            password2: form.password2.value,
            email: form.email.value
        }
        let response = await postQuery(url, data, false)
        if (response.status === 200) {
            let response_data = await response.json()
            if ('error' in response_data) {
                let error = response_data['error']
                let error_msg = response_data['error_msg']
                if (error == 'username') {
                    name_registration_msg.innerHTML = error_msg
                    name_registration_msg.style.display = 'block'
                } else if (error == 'email') {
                    email_registration_msg.innerHTML = error_msg
                    email_registration_msg.style.display = 'block'
                } else if (error == 'password') {
                    passwrod_registration_msg.innerHTML = error_msg
                    passwrod_registration_msg.style.display = 'block'
                }
            } else {
                registration_button.style.borderStyle = 'none'
                registration_button.style.background = '#8ac858'
                registration_button.innerHTML = 'Успешно'
                await new Promise(resolve => setTimeout(resolve, 1000));
                registration_button.style.background = ''
                registration_button.style.borderStyle = ''
                registration_button.innerHTML = 'Регистрация'
                registration_form.style.display = 'none'
                login_form.style.display = 'grid'
                location.reload()
            }
        }
    }
})
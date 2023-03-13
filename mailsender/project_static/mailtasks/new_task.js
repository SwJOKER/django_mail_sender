window.addEventListener('load', (event) => {
    $('#id_subscribers_list, #id_template').change(check_template);

    async function check_template(event) {
        if (id_subscribers_list.value && id_template.value) {
            let data = {
                template_pk: id_template.value,
                subscribers_list_pk: id_subscribers_list.value
                };
            let response = await fetch(check_template_url, {
                method: "POST",
                body: JSON.stringify(data),
                withCredentials: true,
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
            });
            let er_div = $('#template_error');
            er_div.css('display', 'none');
            if (response.status === 200) {
                let response_data = await response.json();
                let res = response_data['result'];
                let message = response_data['message'];
                if (res == false) {
                    er_div.css('display','block');
                    er_div.html(message);
                } else {
                    er_div.css('display','none');
                }
            } else if (response.status == 406) {
                let response_data = await response.json();
                let message = response_data['message'];
                let res = response_data['result'];
                if (res == false) {
                    er_div.css('display','block');
                    er_div.html(message);
                }
            }
        }
    }
})
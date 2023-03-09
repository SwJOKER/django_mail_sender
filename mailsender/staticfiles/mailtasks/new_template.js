window.addEventListener('load', (event) => {

    let reader = new FileReader();
    reader.addEventListener("load", () => {
        CKEDITOR.instances['id_body'].setData(reader.result);
     });

    function put_text_from_file(event) {
        reader.readAsText(event.target.files[0]);
    }

    function erase_val(event) {
        event.target.value = '';
    }

    html_file.addEventListener('click', erase_val);
    html_file.addEventListener('change', put_text_from_file);
    $('#id_subscribers_list').css('color', 'gray');
    $('#id_subscribers_list option').css('color', 'black');
    id_subscribers_list.addEventListener('change', get_variables);
    id_subscribers_list.dispatchEvent(new Event('change'));
    async function get_variables(event) {
        if (id_subscribers_list.value) {
            $('#id_subscribers_list').css('color', 'black');
            $('#id_subscribers_list option').css('color', 'black');

            let data = {pk: id_subscribers_list.value};
            let response = await fetch(var_url, {
                method: "POST",
                body: JSON.stringify(data),
                withCredentials: true,
                headers: {
                    'X-CSRFToken': csrftoken,
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
            });
            let response_data = await response.json();
            custom_complete_items = response_data;
        } else {
            $('#id_subscribers_list').css('color', 'gray');
            $('#id_subscribers_list option').css('color', 'black');
            custom_complete_items = [];
        }
    }
})
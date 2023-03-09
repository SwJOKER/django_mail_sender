window.addEventListener('load', (event) => {
    // get form template and total number of forms from management form
    const templateForm = document.getElementById('id_formset_empty_form');
    const inputTotalForms = document.querySelector('input[id$="-TOTAL_FORMS"]');
    const inputInitialForms = document.querySelector('input[id$="-INITIAL_FORMS"]');

    // get our container (e.g. <table>, <ul>, or <div>) and "Add" button
    const containerFormSet = document.getElementById('id_formset_container');
    const buttonAdd = document.getElementById('id_formset_add_button');
    const buttonSubmit = document.getElementById('id_submit_button');

    // event handlers
    buttonAdd.onclick = addForm;
    buttonSubmit.onclick = updateNameAttributes;

    // form counters (note: proper form index bookkeeping is necessary
    // because django's formset will create empty forms for any missing
    // indices, and will discard forms with indices >= TOTAL_FORMS, which can
    // lead to funny behavior in some edge cases)
   // const initialForms = Number(inputTotalForms.value);
    const initialForms = Number(inputInitialForms.value) == 0? 1: Number(inputInitialForms.value);
    let extraFormIndices = [];
    let nextFormIndex = initialForms;
    let extra_formset_forms = document.querySelectorAll('tr[data-form-index]')
    extra_formset_forms.forEach(element => {
        let index = element.getAttribute('data-form-index')
        if (index >= initialForms && index > 0) {
            setDeleteHandler(element);
        };
    });


    function addForm () {
        // create DocumentFragment from template
        const formFragment = templateForm.content.cloneNode(true);
        // a django form is rendered as_table (default), as_ul, or as_p, so
        // the fragment will contain one or more <tr>, <li>, or <p> elements,
        // respectively.
        for (let element of formFragment.children) {
            // replace the __prefix__ placeholders from the empty form by the
            // actual form index
            element.innerHTML = element.innerHTML.replace(
                /(?<=\w+-)(__prefix__|\d+)(?=-\w+)/g,
                nextFormIndex.toString());
            // add a custom attribute to simplify bookkeeping
            element.dataset.formIndex = nextFormIndex.toString();
            // add a delete click handler (if formset can_delete)
            setDeleteHandler(element);
        }
        // move the fragment's children onto the DOM
        // (the fragment is empty afterwards)
        containerFormSet.appendChild(formFragment);
        // keep track of form indices
        extraFormIndices.push(nextFormIndex++);
        updateTotalFormCount();
    }

    function removeForm (event) {
        // remove all elements with form-index matching that of the delete-input
        const formIndex = event.target.dataset.formIndex;
        for (let element of getFormElements(formIndex)) {
            element.remove();
        }
        // remove form index from array
        let indexIndex = extraFormIndices.indexOf(Number(formIndex));
        if (indexIndex > -1) {
            extraFormIndices.splice(indexIndex, 1);
        }
        updateTotalFormCount();
    }

    function setDeleteHandler (containerElement) {
        // modify DELETE checkbox in containerElement, if the checkbox exists
        // (these checboxes are added by formset if can_delete)
        const inputDelete = containerElement.querySelector('input[id$="-DELETE"]');
        if (inputDelete) {
            // duplicate the form index instead of relying on parentElement (more robust)
            inputDelete.dataset.formIndex = containerElement.dataset.formIndex;
            inputDelete.onclick = removeForm;
        }
    }

    function getFormElements(index) {
        // the data-form-index attribute is available as dataset.formIndex
        // https://developer.mozilla.org/en-US/docs/Learn/HTML/Howto/Use_data_attributes#javascript_access
        return containerFormSet.querySelectorAll('[data-form-index="' + index + '"]');
    }

    function updateNameAttributes (event) {
        // make sure the name indices are consecutive and smaller than
        // TOTAL_FORMS (the name attributes end up as dict keys on the server)
        // note we do not need to update the indices in the id attributes etc.
        for (let [consecutiveIndex, formIndex] of extraFormIndices.entries()) {
            for (let formElement of getFormElements(formIndex)){
                for (let element of formElement.querySelectorAll('input, select')) {
                    if ('name' in element) {
                        element.name = element.name.replace(
                            /(?<=\w+-)(__prefix__|\d+)(?=-\w+)/g,
                            (initialForms + consecutiveIndex).toString());
                    }
                }
            }
        }
        updateTotalFormCount();
    }

    function updateTotalFormCount (event) {
        // note we could simply do initialForms + extraFormIndices.length
        // to get the total form count, but that does not work if we have
        // validation errors on forms that were added dynamically
        const firstElement = templateForm.content.querySelector('input, select');
        // select the first input or select element, then count how many ids
        // with the same suffix occur in the formset container
        if (firstElement) {
            let suffix = firstElement.id.split('__prefix__')[1];
            let selector = firstElement.tagName.toLowerCase() + '[id$="' + suffix + '"]';
            let allElementsForId = containerFormSet.querySelectorAll(selector);
            // update total form count
            inputTotalForms.value = allElementsForId.length;
        }
    }
}, false);
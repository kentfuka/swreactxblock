/* Javascript for SWREACTXBlock.
 * TODO:  Enforce assignment due date for not starting another attempt.
 *        Disble Hint and ShowMe buttons if options are set.
 */
function SWREACTXStudent(runtime, element) {

    console.info("SWREACTXStudent start");
    var handlerUrlGetData = runtime.handlerUrl(element, 'get_data');

    console.info("SWREACTXStudent calling get_data at ",handlerUrlGetData);

    get_data_data = {}		// don't need to sent any data to get_data
        
    $.ajax({
        type: "POST",
        url: handlerUrlGetData,
        data: JSON.stringify(get_data_data),
        error: function(XMLHttpRequest, textStatus, errorThrown) { 
               console.info("SWREACTXstudent get_data POST error textStatus=",textStatus," errorThrown=",errorThrown);
               // alert("Status: " + textStatus); alert("Error: " + errorThrown); 
        },
        success: function (data,msg) {
            console.info("SWREACTXstudent GET success");
            console.info("SWREACTXstudent GET data",data);
            console.info("SWREACTXstudent GET msg",msg);

            var data_obj = JSON.parse(data);
            console.info("SWREACTXstudent GET data_obj",data_obj);

            // Set our context variables from the data we receive
            var question = data_obj.question;
            var grade = data_obj.grade;
            var solution = data_obj.solution;
            var count_attempts = data_obj.count_attempts;
            var variants_count = data_obj.variants_count;
            var max_attempts = data_obj.max_attempts;
            var enable_showme = question.q_option_showme;
            var enable_hint = question.q_option_hint;
            var weight = question.q_weight;
            var min_steps = question.q_grade_min_steps_count;
            var min_steps_ded = question.q_grade_min_steps_ded;
        
            console.info("SWREACTXStudent question",question);
            // console.info("SWREACTXStudent enable_showme",enable_showme);
            // console.info("SWREACTXStudent enable_hint",enable_hint);
            console.info("SWREACTXStudent solution",solution);
            console.info("SWREACTXStudent count_attempts",count_attempts);
            console.info("SWREACTXStudent variants_counnt",variants_count);
            console.info("SWREACTXStudent max_attempts",max_attempts);
            console.info("SWREACTXStudent weight ",weight);
            console.info("SWREACTXStudent min steps",min_steps);
            console.info("SWREACTXStudent min steps dec",min_steps_ded);
            console.info("SWREACTXStudent grade",grade);
        
            if (typeof enable_showme === 'undefined') {
                // console.info("enable_showme is undefined");
                enable_showme = true;
            };
            if (typeof enable_hint === 'undefined') {
                // console.info("enable_hint is undefined");
                enable_hint = true;
            };
        
            var handlerUrl = runtime.handlerUrl(element, 'save_grade');
            console.info("SWREACTXStudent handlerUrl",handlerUrl);
            var handlerUrlStart = runtime.handlerUrl(element, 'start_attempt');
            console.info("SWREACTXStudent handlerUrlStart",handlerUrlStart);
            var handlerUrlRetry = runtime.handlerUrl(element, 'retry');
            console.info("SWREACTXStudent handlerUrlRetry",handlerUrlRetry);

            // Get Primary Element Handles
            var swreactxblock_block = $('.swreactxblock_block', element)[0];
            var stepwise_element = $('querium', element)[0];
        
            // Get Active Preview Element Handles
            var preview_element;
        
            preview_element = set_preview_element();
        
            // Show the active question preview
            preview_element.classList.remove("preview_hidden");
            preview_element.onclick = previewClicked;
        
            // Get Statistics Element Handles
            var question_stats = $('.question-stats', swreactxblock_block)[0];
            var star_box = $('.star-box', swreactxblock_block)[0];
            var star1 = $('.star1', swreactxblock_block)[0];
            var star2 = $('.star2', swreactxblock_block)[0];
            var star3 = $('.star3', swreactxblock_block)[0];
            var elapsed_time_count = $('.elapsed-time-count', swreactxblock_block)[0];
            var grade_val = $('.grade-val', swreactxblock_block)[0];
            var error_count = $('.error-count', swreactxblock_block)[0];
            var hint_count = $('.hint-count', swreactxblock_block)[0];
            var used_showme = $('.used-showme', swreactxblock_block)[0];
        
            // Get Top Element Handles
            var made_attempts = $('.made-attempts', swreactxblock_block)[0];
            var min_steps_element = $('.min-steps', swreactxblock_block)[0];
            // var variants_left = $('.variants-left', swreactxblock_block)[0];
            // var click_to_begin = $('.click-to-begin', swreactxblock_block)[0];
            // var question_info = $('.question-info', swreactxblock_block)[0];
            // var too_many_attempts = $('.too-many-attempts', swreactxblock_block)[0];
        
            // Get Solution Element Handles
            var solution_element = $('.solution', element)[0];
        
            // Get Retry Button Handles
            // var retry_button = $('.stepwise-retry', swreactxblock_block)[0];
            var retry_button_variants = $('.stepwise-retry-variants', swreactxblock_block)[0];
        
            // Overall StepWise UI Handles
            // var xblock_student_view = $('.xblock-student_view', swreactxblock_block)[0];
        
        
            retry_data = {
                q_index: question.q_index
            }
        
            console.info("retry JSON data",JSON.stringify(retry_data));
        
            // Don't allow clicks on the info at the top above the question stimulus
            $('.question-info').onclick = null;
            $('.click-to-begin').onclick = null;
            $('.click-to-begin-box').onclick = null;
            $('.click-to-begin').prop('disabled', true);
            $('.click-to-begin-box').prop('disabled', true);
        
            $('.loading-box').hide();	// Done loading data
            $('.question-info').show();	// Show question info box now that loading is done

            if (max_attempts == -1 || count_attempts < max_attempts) {
                $('.click-to-begin').show();
                $('.xblock-student_view').onclick = null;		// Can't click on the UI
                $('.too-many-attempts').hide();
                $('.too-many-attempts').onclick = null;
                // Show the active question preview
                preview_element.classList.remove("preview_hidden");
                preview_element.onclick = previewClicked;
                console.info('preview_element',preview_element);
                console.info('setting retry click function');
                $('.retry').prop('disabled', false);			// Let them click Retry
                // $('.retry').onclick = retryClicked;
                $('.retry').click(function() {
                  console.info('retry button clicked');
                  console.info("retry JSON data",JSON.stringify(retry_data));
                  $.ajax({
                      type: "POST",
                      url: handlerUrlRetry,
                      data: JSON.stringify(retry_data),
                      success: function (data) {
                          console.info("SWREACTXstudent retry POST success");
                          console.info("SWREACTXstudent retry POST data",data);
                          question_obj = JSON.parse(data);
                          question = question_obj.question;
                          console.info("SWREACTXstudent retry POST response question",question);
                          preview_element = set_preview_element();
                          console.info("SWREACTXstudent retry POST new preview_element",preview_element);
                      }
                  });
                  console.info("retry button click ended");
                });
                console.info('enabled retry button');
            } else {
                $('.click-to-begin').hide();
                $('.too-many-attempts').show();
                $('.too-many-attempts').onclick = null;
                preview_element.classList.add("preview_hidden");	// Don't show another preview
                preview_element.onclick = null;				// Don't let them click again
                console.info('preview_element',preview_element);
                console.info('setting retry click function');
                $('.retry').prop('disabled', true);			// Don't let them click Retry
                // $('.retry').onclick = retryClicked;
                $('.retry').click(function() {
                  console.info('empty eset button clicked');
                });
                console.info('disabled eset button');
            }
        
            // Init preview mode
            updateStats();
            updateSolution();
            updateTopInfo();
            
            function set_preview_element() {
        
                console.log('set_preview_element hide old preview_element preview_element=',preview_element);
        
                if (typeof preview_element !== 'undefined') {
                     preview_element.classList.add("preview_hidden");	// Hide old element if it exists
                };
        
                // Hide old display_math
                // display_math = $('.display-math', preview_element)[0];
                // display_math.classList.add("preview_hidden");
        
                switch( question.q_index ){
                    case 0:
                        preview_element = $('.qq_preview0', element)[0];
                        break;
                    case 1:
                        preview_element = $('.qq_preview1', element)[0];
                        break;
                    case 2:
                        preview_element = $('.qq_preview2', element)[0];
                        break;
                    case 3:
                        preview_element = $('.qq_preview3', element)[0];
                        break;
                    case 4:
                        preview_element = $('.qq_preview4', element)[0];
                        break;
                    case 5:
                        preview_element = $('.qq_preview5', element)[0];
                        break;
                    case 6:
                        preview_element = $('.qq_preview6', element)[0];
                        break;
                    case 7:
                        preview_element = $('.qq_preview7', element)[0];
                        break;
                    case 8:
                        preview_element = $('.qq_preview8', element)[0];
                        break;
                    case 9:
                        preview_element = $('.qq_preview9', element)[0];
                        break;
                    default:
                        preview_element = $('.qq_preview0', element)[0];
                }
        
                console.log('set_preview_element reveal new preview_element');
        
                // Reveal new variant
                preview_element.classList.remove("preview_hidden");
        
                // Reveal New Display Math if empty
                display_math = $('.display-math', preview_element)[0];
                if ( display_math.innerText.length>5 ){
                    display_math.classList.remove("preview_hidden");
                }else{
                    display_math.classList.add("preview_hidden");
                }
        
                // Enable clicks on the new variant if we have attempts left
        	console.log('set_preview_element count_attempts=',count_attempts,' max_attempts=',max_attempts);
                if (max_attempts == -1 || count_attempts < max_attempts) {
                    preview_element.onclick = previewClicked;
                } else {
                    preview_element.onclick = null
                }
        
                return preview_element;
            };
        
            function previewClicked(){ 
                var options = {
                    // hideMenu: true,
                    showMe: enable_showme,
                    hint: enable_hint,
                    policies: 'NONE'		// We set this later
                    // assessing: false
                    // scribbles: false
                };
        
                console.info("SWREACTXstudent previewClicked() started");
                console.info("SWREACTXstudent previewClicked() count_attempts ",count_attempts);
                console.info("SWREACTXstudent previewClicked() max_attempts ",max_attempts);
                // console.info("SWREACTXstudent previewClicked() weight ",weight);
                // console.info("SWREACTXstudent previewClicked() min_steps ",min_steps);
                // console.info("SWREACTXstudent previewClicked() min_steps_ded ",min_steps_ded);
                // Don't let student launch question if they've exceeded the limit on question attempts
                if (max_attempts != -1 && count_attempts >= max_attempts) {
                    console.info("SWREACTXstudent previewClicked() too many attempts");
                    $('.click-to-begin').hide();
                    $('.too-many-attempts').show();
                    $('.too-many-attempts').onclick = null;
                    $('.retry').hide();
                    $('.retry').onclick = null;
                    return;
                };
                // count_attempts++;  // no need to do this here, since the Python code does update this
        
                if (enable_showme == true && enable_hint == true) {
                    options.policies = '$A1$';
                } else if (enable_showme == true && enable_hint == false) {
                    options.policies = '{$A1$, Hold[clearPolicy[showMeAvailable]] }';   // There is no standard name for this
                } else if (enable_showme == false && enable_hint == true) {
                    options.policies = '$A2$';
                } else {  // false and false
                    options.policies = '$A5$';
                };
                console.info("SWREACTXstudent previewClicked() options.policies set to",options.policies);
        
                function celebrate(stats) {
                    swreactxblock_block.classList.remove("block_working");
                    swreactxblock_block.classList.add("block_worked");
        
                    console.info("Celebrate", stats);
                    solution = stats;
                    solution.answered_question = question; // remember the question we answered for the stats display
                    // console.info("celebrate solution ", solution);
        
                    // NOTE: We compute the grade here for display purposes, but the Python code on the server also calculates the grade itself.
                    //       We could pass all of this info over to the server to avoid this duplication of code, provided we trust these browser-based calcs.
        
                    grade = 3.0;
                    console.log('start grade calc stats.errors=',stats.errors,' question.q_grade_errors_count=',question.q_grade_errors_count,' question.q_grade_errors_ded=',question.q_grade_errors_ded);
                    if (stats.errors>question.q_grade_errors_count) {
                        grade=grade-question.q_grade_errors_ded;
                    }
                    console.log('stats.hints=',stats.hints,' question.q_grade_hints_count=',question.q_grade_hints_count,' question.q_grade_hints_ded=',question.q_grade_hints_ded);
                    if (stats.hints>question.q_grade_hints_count) {
                        grade=grade-question.q_grade_hints_ded;
                    }
                    console.log('stats.usedShowMe=',stats.usedShowMe,' question.q_grade_showme_ded=',question.q_grade_showme_ded);
                    if (stats.usedShowMe) {
                        grade=grade-question.q_grade_showme_ded;
                        console.info('used showme');
                    }
        
                    //  Count valid steps
        
                    var c, i;
                    var valid_step_count = 0;
        
                    for( c=0; c<solution.stepDetails.length; c++){
                        for( i=0; i<solution.stepDetails[c].info.length; i++){
                            console.info('i=',i,' c=',c,' info=',solution.stepDetails[c].info[i])
                            switch( solution.stepDetails[c].info[i].status ){
                                case 0: // victory
                                    valid_step_count++;
                                    break;
                                case 1: // valid step
                                    valid_step_count++;
                                    break;
                                case 3: // invalid step
                                    break;
                                case 4: // hint request
                                    break;
                                default:
                                    break;
                            }
                        }
                    }
                    console.log('valid_step_count=',valid_step_count);
                    console.log('question.q_definition=',question.q_definition);
                    console.log('question.q_grade_min_steps_count=',question.q_grade_min_steps_count,' question.q_grade_min_steps_ded=',question.q_grade_min_steps_ded);
                    console.log('question.q_grade_min_steps_count=',question.q_grade_min_steps_count,' question.q_grade_min_steps_ded=',question.q_grade_min_steps_ded);
        
                    // console.log('question.q_definition=',question.q_definition);
                    // console.log('question.q_definition.indexOf("MatchSpec")=',question.q_definition.indexOf('MatchSpec'));
                    if (grade >= 3.0 && valid_step_count < question.q_grade_min_steps_count && question.q_definition.indexOf('MatchSpec') == -1 && question.q_definition.indexOf('DomainOf') == -1) {
                        grade=grade-question.q_grade_min_steps_ded;
                        console.log('took min_steps deduction after grade=',grade);
                    } else {
                        console.log('did not take min_steps deduction after grade=',grade);
                    }
        
                    updateStats();
                    updateSolution();
                    updateTopInfo();
        
                    preview_element.classList.remove("preview_hidden");
                    stepwise_element.style.display = 'none';
        
                    stats.grade = grade;
        
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
                    $.ajax({
                        type: "POST",
                        url: handlerUrl,
                        data: JSON.stringify(stats),
                        success: null
                    });
                }
                    
                // Callback when the student begins to work on a problem (e.g. enters a step, clicks "Hint", clicks "Show Solution"
                function start_attempt(status) {
        
                    console.info("start_attempt sessionId=",status.sessionId," timeMark=",status.timeMark," action=",a=status.action)
                    console.info("start_attempt question.q_index=",question.q_index)
        
                    start_attempt_data = {
                        status: status,
                        q_index: question.q_index
                    }
        
                    console.info("start_attempt JSON data",JSON.stringify(start_attempt_data));
        
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
                    $.ajax({
                        type: "POST",
                        url: handlerUrlStart,
                        data: JSON.stringify(start_attempt_data),
                        success: function (data) {
                          console.info("SWREACTXstudent start_attempt POST success");
                          start_attempt_obj = JSON.parse(data);
                          count_attempts = start_attempt_obj.count_attempts;
                          update_grade_attempts_data();
                          console.info("SWREACTXstudent start_attempt POST response count_attempts=",count_attempts);
                      }
                    });
                }
        
                var callbacks = {
                    success: celebrate,
                    start: start_attempt
                };
            
                var qDef = {
                    id: ( question.q_id ? question.q_id : false ),
                    label: ( question.q_label ? question.q_label : "" ),
                    description: question.q_stimulus,
                    definition: question.q_definition,
                    type: question.q_type,
                    mathml: question.q_display_math,
                    hint1: question.q_hint1,
                    hint2: question.q_hint2,
                    hint3: question.q_hint3
                };
            
                preview_element.classList.add("preview_hidden");
                question_stats.classList.add("preview_hidden");
                solution_element.classList.add("preview_hidden");
        
                stepwise_element.style.display = 'block';
                swreactxblock_block.classList.add("block_working");
                swreactxblock_block.classList.remove("block_worked");
                setTimeout( function(){
                    swreactxblock_block.scrollIntoView({ behavior:"smooth"});
                }, 250);
        
                console.info("SWREACTXblock previewClicked() calling querium.startQuestion with options ",options);
                querium.startQuestion( 'OpenStaxHomework', sId, qDef, callbacks, options, stepwise_element );    // launch!
        
            }   
        
            function retryClicked(){
                console.info("SWREACTXstudent retryClicked() started");
                $.ajax({
                    type: "POST",
                    url: handlerUrlRetry,
                    // data: JSON.stringify(),
                    success: function (data,msg) {
                        console.info("SWREACTXstudent retry POST success");
                        console.info("SWREACTXstudent retry POST data",data);
                        console.info("SWREACTXstudent retry POST msg",msg);
                    }
                });
                console.info("SWREACTXstudent retryClicked() ended");
            }
        
            // NOT USED AT PRESENT
            //success Type: Function( PlainObject data, String textStatus, jqXHR jqXHR )
            function retrySuccess(data, textstatus, jqXHR) {
                console.info("SWREACTXstudent retrySuccess() started");
                console.info("SWREACTXstudent retrySuccess() data",data);
                console.info("SWREACTXstudent retrySuccess() textStatus",textStatus);
                console.info("SWREACTXstudent retrySuccess() jqXHR",jqXHR);
                console.info("SWREACTXstudent retrySuccess() ended");
            }
        
            function updateStats(){
                console.info('updateStats:', grade)
                if (grade < 0) {    // Including undefined ie. -1
                        star_box.classList.add("preview_hidden");
                } else if ( grade > 0.0 && grade < 0.5 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.remove('full');
                        star2.classList.remove('half');
                        star2.classList.remove('full');
                        star3.classList.remove('half');
                        star3.classList.remove('full');
                } else if ( grade >= 0.5 && grade < 1.0 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.add('half');
                        star1.classList.remove('full');
                        star2.classList.remove('half');
                        star2.classList.remove('full');
                        star3.classList.remove('half');
                        star3.classList.remove('full');
                } else if ( grade >= 1.0 && grade < 1.5 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.add('full');
                        star2.classList.remove('half');
                        star2.classList.remove('full');
                        star3.classList.remove('half');
                        star3.classList.remove('full');
                } else if ( grade >= 1.5 && grade < 2.0 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.add('full');
                        star2.classList.add('half');
                        star2.classList.remove('full');
                        star3.classList.remove('half');
                        star3.classList.remove('full');
                } else if ( grade >= 2.0 && grade < 2.5 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.add('full');
                        star2.classList.remove('half');
                        star2.classList.add('full');
                        star3.classList.remove('half');
                        star3.classList.remove('full');
                } else if ( grade >= 2.5 && grade < 3.0 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.add('full');
                        star2.classList.remove('half');
                        star2.classList.add('full');
                        star3.classList.add('half');
                        star3.classList.remove('full');
                } else if ( grade == 3.0 ) {
                        star_box.classList.remove("preview_hidden");
                        star1.classList.remove('half');
                        star1.classList.add('full');
                        star2.classList.remove('half');
                        star2.classList.add('full');
                        star3.classList.remove('half');
                        star3.classList.add('full');
                } else if ( grade > 3.0 ) {
                        star_box.classList.add("preview_hidden");
                        console.error('bad grade value > 3.0:', grade)
                }
        
                if( grade==-1 ){
                    question_stats.classList.add("preview_hidden");
                }else{
                    question_stats.classList.remove("preview_hidden");
                    elapsed_time_count.innerText = solution.time.toFixed(0);
                    update_grade_attempts_data();
                    if( solution.usedShowMe ){
                        used_showme.classList.remove("preview_hidden");
                    }else{
                        used_showme.classList.add("preview_hidden");
                    }    
                }
            }
        
            function update_grade_attempts_data(){
                grade_string = '('+((grade/3.0)*weight).toFixed(2)+'/'+weight.toFixed(2)+' point';
                if (weight > 1.0) {
                    grade_string = grade_string + 's)';
                } else {
                    grade_string = grade_string + ')';
                }
                grade_val.innerText = grade_string;
                error_count.innerText = solution.errors;
                hint_count.innerText = solution.hints;
                var attempts_string;
                attempts_string = count_attempts;
                attempts_string += ' of ';
                if( max_attempts == -1) {
                   attempts_string += 'unlimited';
                }else{
                   attempts_string += max_attempts;
                }
                attempts_string += ' attempts';
                console.info('update_grade_attempts_data grade_string=',grade_string,' attempts_string=',attempts_string);
                made_attempts.innerText = attempts_string;

		if (min_steps == null || min_steps <= 0) {
                     $('.min-steps-box').hide();		// Don't show min-steps box
                }else{
                    min_steps_string = min_steps;
                    min_steps_string += ' minimum steps';
                    min_steps_element.innerText = min_steps_string;
                }
            }

            function updateSolution(){
                console.info("updateSolution. grade=",grade);
                if( grade==-1 ){ return; }
        
                // kill solution_element's children
                while (solution_element.firstChild) {
                    solution_element.removeChild(solution_element.firstChild);
                }
        
                // Display the stimulus of the problem corresponding to these steps, since the question variant shown may be different
                // than the one used in the attempt associated with these steps/stats.
                var stimulus_el, stimulus_el_text, stimulus_el_problem, stimulus_el_math;
                if (typeof solution.answered_question === 'undefined') {
                    console.info("solution.answered_question is undefined");
                } else {
                    stimulus_el = document.createElement("div");
                    stimulus_el.classList.add("stimulus");
                    stimulus_el_text = document.createElement("div");
                    stimulus_el_text.classList.add("last-attempt-text");
                    stimulus_el_text.innerText= "Your last problem attempt was:";
                    stimulus_el_problem = document.createElement("div");
                    stimulus_el_problem.classList.add("stimulus-problem");
                    stimulus_el_problem.innerHTML= solution.answered_question.q_stimulus;
                    stimulus_el_math = document.createElement("div");
                    stimulus_el_math.classList.add("stimulus-math");
                    stimulus_el_math.innerText= solution.answered_question.q_display_math;
                    stimulus_el.appendChild(stimulus_el_text);
                    stimulus_el.appendChild(stimulus_el_problem);
                    stimulus_el.appendChild(stimulus_el_math);
                    solution_element.appendChild(stimulus_el);
                };
        
                // build array of steps
                let step_list = [];
                var c, i, et;
                var new_step_el, step_time_el, step_type_el, step_text_el;
        
                for( c=0; c<solution.stepDetails.length; c++){
                    for( i=0; i<solution.stepDetails[c].info.length; i++){
                        // console.info( solution.stepDetails[c].info[i])
                        // step wrapper
                        new_step_el = document.createElement("div");
                        new_step_el.classList.add("step-container");
        
                        // time of step
                        step_time_el = document.createElement("div");
                        step_time_el.classList.add("step-time");
                        et = solution.stepDetails[c].info[i].time/1000;
                        step_time_el.innerText= et.toFixed() + "s";
        
                        // step details
                        step_type_el = document.createElement("div");
                        step_type_el.classList.add("step-icon");
                        step_text_el = document.createElement("div");
                        step_text_el.classList.add("step-text");
        
                        switch( solution.stepDetails[c].info[i].status ){
                            case 0: // victory
                                step_type_el.classList.add("question-completed");
                                step_text_el.innerHTML=solution.stepDetails[c].info[i].mathML
                                break;
                            case 1: // valid step
                                step_type_el.classList.add("valid-step");
                                step_text_el.innerHTML=solution.stepDetails[c].info[i].mathML
                                break;
                            case 3: // invalid step
                                step_type_el.classList.add("invalid-step");
                                step_text_el.innerHTML=solution.stepDetails[c].info[i].mathML
                                break;
                            case 4: // hint request
                                step_type_el.classList.add("hint-request");
                                step_text_el.innerHTML=badMathmlFix(solution.stepDetails[c].info[i].text);
                                break;
                            default:
                                console.error(solution.stepDetails[c].info[i]);
                        }
        
                        // assemble elements
                        new_step_el.appendChild(step_time_el);
                        new_step_el.appendChild(step_type_el);
                        new_step_el.appendChild(step_text_el);
                        solution_element.appendChild(new_step_el);
                    }
                }
                
                if( grade==-1){
                    console.info('grade is -1. hiding solution')
                    solution_element.classList.add("preview_hidden");
                }else{
                    console.info('showing solution')
                    solution_element.classList.remove("preview_hidden");
                    MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
                }
            }
        
            // Update question top info
        
            function updateTopInfo() {
        
                // Show question points/weight
                if (grade == -1) {
                    grade_string = '(0.00/'+weight.toFixed(2)+' point';
                } else {
                    grade_string = '('+((grade/3.0)*weight).toFixed(2)+'/'+weight.toFixed(2)+' point';
                }
                if (weight > 1.0) {
                    grade_string = grade_string + 's)';
                } else {
                    grade_string = grade_string + ')';
                }
                grade_val.innerText = grade_string;
        
                // Show attempts and no attempts message
        
                var attempts_string;
                attempts_string = count_attempts;
                attempts_string += ' of ';
                if( max_attempts == -1) {
                           attempts_string += 'unlimited';
                }else{
                           attempts_string += max_attempts;
                }
                attempts_string += ' attempts';
                console.info('initial attempts_string',attempts_string);
                console.info('and initial made_attempts',made_attempts);
                console.info('and initial min_steps',min_steps);
                made_attempts.innerText = attempts_string;
        
		if (min_steps == null || min_steps <= 0) {
                     $('.min-steps-box').hide();		// Don't show min-steps box
                }else{
                    min_steps_string = min_steps;
                    min_steps_string += ' minimum steps';
                    min_steps_element.innerText = min_steps_string;
                }

                // Show total variants below the Retry button
                var variants_string = '(';
                variants_string += variants_count;
                variants_string += ' variant'
                if (variants_count > 1) {
                   variants_string += 's)';
                } else {
                   variants_string += ')';
                };
                retry_button_variants.innerText = variants_string;
            }
        
        
            // StepWise hints can contain bath <mspace> tags and badly escaped > at the end of mathml tags
            function badMathmlFix( s ) {
                // console.debug( 'badmathmlfix in s=',s);
                var goods = s.replace(new RegExp('mspace width=\'\\.\\d+em\'', 'g'), 'MSPACE').replace(new RegExp('MSPACE\\\\', 'g'), 'MSPACE').replace(new RegExp('MSPACE','g'),'mspace width=\'.04em\'').replace(new RegExp('\\\>', 'g'), '>');
                // console.debug( 'badmathmlfix out s=',goods);
                return goods;
            }
        
            // set student id
            var sId = ( question.q_user.length>1 ? question.q_user : "UnknownStudent");
        
            // console.info( sId );
        
            /* PAGE LOAD EVENT */
            $(function ($) {
            });
        
            // wrap element as core.js may pass a raw element or an wrapped one
            angular.bootstrap($(element), ['querium-stepwise']);
            MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
       }
    });
    console.info("SWREACTXStudent end");
    $('.loading-box').show();        // Show loading box while we wait
    $('.question-info').hide();      // Don't show question info box while we wait
    $('.click-to-begin-box').hide(); // Don't show click to begin msg box while we wait
}

/* Javascript for SWREACTXStudio. */
function SWREACTXStudio(runtime, element, question) {
    // Stub notify so xblock doesnt crash in dev
    if( typeof runtime.notify === "undefined" ){
        runtime.notify = function(){ console.info(arguments); }
    }
 
    var handlerUrl = runtime.handlerUrl(element, 'save_question');

    $('.save-button', element).click(function(eventObject) {
        var data = {

            q_weight : $('#q_weight', element).val(),
            q_max_attempts : $('#q_max_attempts', element).val(),
            q_option_showme : $('#q_option_showme', element).val(),
            q_option_hint : $('#q_option_hint', element).val(),
            q_grade_showme_ded : $('#q_grade_showme_ded', element).val(),
            q_grade_hints_count : $('#q_grade_hints_count', element).val(),
            q_grade_hints_ded : $('#q_grade_hints_ded', element).val(),
            q_grade_errors_count : $('#q_grade_errors_count', element).val(),
            q_grade_errors_ded : $('#q_grade_errors_ded', element).val(),
            q_grade_min_steps_count : $('#q_grade_min_steps_count', element).val(),
            q_grade_min_steps_ded : $('#q_grade_min_steps_ded', element).val(),

            id : $('#id', element).val(),
            label : $('#label', element).val(),
            stimulus : $('#stimulus', element).val(),
            definition : $('#definition', element).val(),
            qtype : $('#qtype', element).val(),
            display_math : $('#display_math', element).val(),
            hint1 : $('#hint1', element).val(),
            hint2 : $('#hint2', element).val(),
            hint3 : $('#hint3', element).val(),

            q1_id : $('#q1_id', element).val(),
            q1_label : $('#q1_label', element).val(),
            q1_stimulus : $('#q1_stimulus', element).val(),
            q1_definition : $('#q1_definition', element).val(),
            q1_qtype : $('#q1_qtype', element).val(),
            q1_display_math : $('#q1_display_math', element).val(),
            q1_hint1 : $('#q1_hint1', element).val(),
            q1_hint2 : $('#q1_hint2', element).val(),
            q1_hint3 : $('#q1_hint3', element).val(),

            q2_id : $('#q2_id', element).val(),
            q2_label : $('#q2_label', element).val(),
            q2_stimulus : $('#q2_stimulus', element).val(),
            q2_definition : $('#q2_definition', element).val(),
            q2_qtype : $('#q2_qtype', element).val(),
            q2_display_math : $('#q2_display_math', element).val(),
            q2_hint1 : $('#q2_hint1', element).val(),
            q2_hint2 : $('#q2_hint2', element).val(),
            q2_hint3 : $('#q2_hint3', element).val(),

            q3_id : $('#q3_id', element).val(),
            q3_label : $('#q3_label', element).val(),
            q3_stimulus : $('#q3_stimulus', element).val(),
            q3_definition : $('#q3_definition', element).val(),
            q3_qtype : $('#q3_qtype', element).val(),
            q3_display_math : $('#q3_display_math', element).val(),
            q3_hint1 : $('#q3_hint1', element).val(),
            q3_hint2 : $('#q3_hint2', element).val(),
            q3_hint3 : $('#q3_hint3', element).val(),

            q4_id : $('#q4_id', element).val(),
            q4_label : $('#q4_label', element).val(),
            q4_stimulus : $('#q4_stimulus', element).val(),
            q4_definition : $('#q4_definition', element).val(),
            q4_qtype : $('#q4_qtype', element).val(),
            q4_display_math : $('#q4_display_math', element).val(),
            q4_hint1 : $('#q4_hint1', element).val(),
            q4_hint2 : $('#q4_hint2', element).val(),
            q4_hint3 : $('#q4_hint3', element).val(),

            q5_id : $('#q5_id', element).val(),
            q5_label : $('#q5_label', element).val(),
            q5_stimulus : $('#q5_stimulus', element).val(),
            q5_definition : $('#q5_definition', element).val(),
            q5_qtype : $('#q5_qtype', element).val(),
            q5_display_math : $('#q5_display_math', element).val(),
            q5_hint1 : $('#q5_hint1', element).val(),
            q5_hint2 : $('#q5_hint2', element).val(),
            q5_hint3 : $('#q5_hint3', element).val(),

            q6_id : $('#q6_id', element).val(),
            q6_label : $('#q6_label', element).val(),
            q6_stimulus : $('#q6_stimulus', element).val(),
            q6_definition : $('#q6_definition', element).val(),
            q6_qtype : $('#q6_qtype', element).val(),
            q6_display_math : $('#q6_display_math', element).val(),
            q6_hint1 : $('#q6_hint1', element).val(),
            q6_hint2 : $('#q6_hint2', element).val(),
            q6_hint3 : $('#q6_hint3', element).val(),

            q7_id : $('#q7_id', element).val(),
            q7_label : $('#q7_label', element).val(),
            q7_stimulus : $('#q7_stimulus', element).val(),
            q7_definition : $('#q7_definition', element).val(),
            q7_qtype : $('#q7_qtype', element).val(),
            q7_display_math : $('#q7_display_math', element).val(),
            q7_hint1 : $('#q7_hint1', element).val(),
            q7_hint2 : $('#q7_hint2', element).val(),
            q7_hint3 : $('#q7_hint3', element).val(),

            q8_id : $('#q8_id', element).val(),
            q8_label : $('#q8_label', element).val(),
            q8_stimulus : $('#q8_stimulus', element).val(),
            q8_definition : $('#q8_definition', element).val(),
            q8_qtype : $('#q8_qtype', element).val(),
            q8_display_math : $('#q8_display_math', element).val(),
            q8_hint1 : $('#q8_hint1', element).val(),
            q8_hint2 : $('#q8_hint2', element).val(),
            q8_hint3 : $('#q8_hint3', element).val(),

            q9_id : $('#q9_id', element).val(),
            q9_label : $('#q9_label', element).val(),
            q9_stimulus : $('#q9_stimulus', element).val(),
            q9_definition : $('#q9_definition', element).val(),
            q9_qtype : $('#q9_qtype', element).val(),
            q9_display_math : $('#q9_display_math', element).val(),
            q9_hint1 : $('#q9_hint1', element).val(),
            q9_hint2 : $('#q9_hint2', element).val(),
            q9_hint3 : $('#q9_hint3', element).val(),
        }

        runtime.notify('save', {state:'start'});
        $.ajax({
            type: "POST",
            url: handlerUrl,
            data: JSON.stringify(data),
            success: null
        }).done( function(response){
            runtime.notify('save', {state:'end'});
        });
    });

    $('.cancel-button', element).click(function(eventObject) {
        runtime.notify('cancel', {});
    });
 
    /* PAGE LOAD EVENT */
    $(function ($) {
    });

}


/* Javascript for SWREACTXAuthor. */
function SWREACTXAuthor(runtime, element, questions) {
    var qu1 = $( "#variant1", element );
    var dm1 = $( ".display_math", qu1 );

    var qu2 = $( "#variant2", element );
    var dm2 = $( ".display_math", qu2 );

    var qu3 = $( "#variant3", element );
    var dm3 = $( ".display_math", qu3 );

    var qu4 = $( "#variant4", element );
    var dm4 = $( ".display_math", qu4 );

    var qu5 = $( "#variant5", element );
    var dm5 = $( ".display_math", qu5 );

    var qu6 = $( "#variant6", element );
    var dm6 = $( ".display_math", qu6 );

    var qu7 = $( "#variant7", element );
    var dm7 = $( ".display_math", qu7 );

    var qu8 = $( "#variant8", element );
    var dm8 = $( ".display_math", qu8 );

    var qu9 = $( "#variant9", element );
    var dm9 = $( ".display_math", qu9 );

    var qu10 = $( "#variant10", element );
    var dm10 = $( ".display_math", qu10 );

    console.info('SWREACTXAuthor questions',questions);

    switch (questions) {
        case 1:
            qu1.removeClass("problem-empty");
            qu2.addClass("problem-empty");
            qu3.addClass("problem-empty");
            qu4.addClass("problem-empty");
            qu5.addClass("problem-empty");
            qu6.addClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 2:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.addClass("problem-empty");
            qu4.addClass("problem-empty");
            qu5.addClass("problem-empty");
            qu6.addClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 3:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.addClass("problem-empty");
            qu5.addClass("problem-empty");
            qu6.addClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 4:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.addClass("problem-empty");
            qu6.addClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 5:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.addClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 6:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.removeClass("problem-empty");
            qu7.addClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 7:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.removeClass("problem-empty");
            qu7.removeClass("problem-empty");
            qu8.addClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 8:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.removeClass("problem-empty");
            qu7.removeClass("problem-empty");
            qu8.removeClass("problem-empty");
            qu9.addClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 9:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.removeClass("problem-empty");
            qu7.removeClass("problem-empty");
            qu8.removeClass("problem-empty");
            qu9.removeClass("problem-empty");
            qu10.addClass("problem-empty");
            break;
        case 10:
            qu1.removeClass("problem-empty");
            qu2.removeClass("problem-empty");
            qu3.removeClass("problem-empty");
            qu4.removeClass("problem-empty");
            qu5.removeClass("problem-empty");
            qu6.removeClass("problem-empty");
            qu7.removeClass("problem-empty");
            qu8.removeClass("problem-empty");
            qu9.removeClass("problem-empty");
            qu10.removeClass("problem-empty");
            break;
    }

    if( dm1.html()=="\\(\\)" ){
        dm1.addClass("problem-empty");
    }else{
        dm1.removeClass("problem-empty");
    }

    if( dm2.html()=="\\(\\)" ){
        dm2.addClass("problem-empty");
    }else{
        dm2.removeClass("problem-empty");
    }

    if( dm3.html()=="\\(\\)" ){
        dm3.addClass("problem-empty");
    }else{
        dm3.removeClass("problem-empty");
    }

    if( dm4.html()=="\\(\\)" ){
        dm4.addClass("problem-empty");
    }else{
        dm4.removeClass("problem-empty");
    }

    if( dm5.html()=="\\(\\)" ){
        dm5.addClass("problem-empty");
    }else{
        dm5.removeClass("problem-empty");
    }

    if( dm6.html()=="\\(\\)" ){
        dm6.addClass("problem-empty");
    }else{
        dm6.removeClass("problem-empty");
    }

    if( dm7.html()=="\\(\\)" ){
        dm7.addClass("problem-empty");
    }else{
        dm7.removeClass("problem-empty");
    }

    if( dm8.html()=="\\(\\)" ){
        dm8.addClass("problem-empty");
    }else{
        dm8.removeClass("problem-empty");
    }

    if( dm9.html()=="\\(\\)" ){
        dm9.addClass("problem-empty");
    }else{
        dm9.removeClass("problem-empty");
    }

    if( dm10.html()=="\\(\\)" ){
        dm10.addClass("problem-empty");
    }else{
        dm10.removeClass("problem-empty");
    }


    /* PAGE LOAD EVENT */
    $(function ($) {
        MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
        setTimeout(function () {
            console.info(questions)
        }, 250);
    });
}

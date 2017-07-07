/*
  Enable users to switch between viewing and writing CourseTalk reviews.
 */

export class CourseTalkReviews {  // eslint-disable-line import/prefer-default-export
  constructor() {
    const $courseTalkToggleReadWriteReviews = $('.toggle-read-write-reviews');
    const $courseTalkScriptObject = $('.coursetalk-reviews-script');

    const readSrc = '//d3q6qq2zt8nhwv.cloudfront.net/s/js/widgets/coursetalk-read-reviews.js';
    const writeSrc = '//d3q6qq2zt8nhwv.cloudfront.net/s/js/widgets/coursetalk-write-reviews.js';

    $coursetalkToggleReadWriteReviews.on('click', () => {
      // Cache js file for future button clicks
      $.ajaxSetup({ cache: true });

      // Toggle the new coursetalk script object
      const currentSrc = $courseTalkScriptObject.attr('src');
      const newSrc = (currentSrc === readSrc) ? writeSrc : readSrc;
      $courseTalkScriptObject.attr('src', newSrc);
      $.getScript(newSrc);

      // Switch the button text
      const newText = (newSrc === readSrc) ? 'Write a Review' : 'View Reviews';
      $courseTalkToggleReadWriteReviews.text(newText);
    });
  }
}

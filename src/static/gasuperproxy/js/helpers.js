/**
*
* Copyright 2013 Google Inc. All Rights Reserved.
*
* Licensed under the Apache License, Version 2.0 (the "License");
* you may not use this file except in compliance with the License.
* You may obtain a copy of the License at
*
*    http://www.apache.org/licenses/LICENSE-2.0
*
* Unless required by applicable law or agreed to in writing, software
* distributed under the License is distributed on an "AS IS" BASIS,
* WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
* See the License for the specific language governing permissions and
* limitations under the License.
*/


/**
 * @author pete.frisella@gmail.com (Pete Frisella)
 *
 * @fileoverview
 * Helper functions to validate form input and to prompt users before delete
 * operations.
*/


/**
 * Adds event hanlders that will to prompt the user to confirm delete
 * operations.
 */
function initializeDeleteEventHandlers() {
  var deleteQueryForm = document.getElementById('delete_query');
  if (deleteQueryForm) {
    deleteQueryForm.onsubmit = promptDeleteQuery;
  }

  var clearErrorsForm = document.getElementById('clear_errors');
  if (clearErrorsForm) {
    clearErrorsForm.onsubmit = promptClearErrors;
  }
}


/**
 * The event handling function for deleting an API Query.
 * @param {Object} evt The even that took place.
 */
function promptDeleteQuery(evt) {
  confirmFormSubmit('Are you sure you want to delete this query?', evt);
}


/**
 * The event handling function for clearing API Query Error Responses.
 * @param {Object} evt The even that took place.
 */
function promptClearErrors(evt) {
  confirmFormSubmit('Are you sure you want to clear the errors. Has the ' +
      'problem been resolved?', evt);
}


/**
 * Prompts the user with a message to confirm or cancel an event that took
 * place.
 * @param {String} message The message to display to the user.
 * @param {Object} e The event that took place.
 * @return {Boolean} Whether the user confirmed or cancelled the event.
 */
function confirmFormSubmit(message, e) {
  var e = e || window.event;
  var confirmSubmit = confirm(message);
  if (confirmSubmit) {
    return true;
  }
  e.preventDefault();
  return false;
}


/**
 * Intialize event handlers
 */
window.onload = initializeDeleteEventHandlers;


/**
 * Client-side Validation rules for user input.
 *
 * To define a validation rule for form input, use the id of the input element
 * as the Key for the rule.
 * The following rules can be set for each input:
 *  required: Boolean - Indicate whether input is required.
 *  maxLength: Number - Set a maximum length for the input.
 *  min, max: Number - Set a minimum and maximum value for the input. You need
 *      to specify both.
 *  test: RegExp - A regular expression to test against the input. Requires that
 *      you also define a testErrorMsg.
 *  testErrorMsg: String - The error message to display if RegExp test fails.
 *      This is required when a test rule has been set.
 *  msgId: String - The id of the element to write to for any error or status
 *      messages that need to be displayed to the user. This is required.
 *
 * Example: A rule for text input with id=email_address, and a div element to
 * display error messages with id=email_error:
 *  VALIDATION_RULES = {
 *    email_address: {
 *      required: true,
 *      maxLength: 256,
 *      test: /.+\@.+\..+/,
 *      testErrorMsg: 'Please enter a valid email address.',
 *      msgId: email_error
 *    }
 *  }
 *
 * <form>
 *  <input id="email_address" type="text"/>
 *  <span id="email_error"></span>
 */
VALIDATION_RULES = {
  name: {
    required: true,
    maxLength: 115,
    msgId: 'name_msg'
  },
  refresh_interval: {
    required: true,
    min: 15,
    max: 2505600,
    msgId: 'refresh_interval_msg',
    test: /^\d+$/,
    testErrorMsg: 'Please enter only digits.'
  },
  request: {
    required: true,
    maxLength: 2000,
    msgId: 'request_msg',
    test: /^(http|https):\/\/(\S+)?$/,
    testErrorMsg: 'Please enter a valid URL.'
  },
  email: {
    required: true,
    maxLength: 256,
    msgId: 'email_msg',
    test: /.+\@.+\..+/,
    testErrorMsg: 'Please enter a valid email address.'
  }
};


/**
 * Checks if a value has been set for input that is required.
 * @param {String} value The value of the input element to check.
 * @param {Array} rules The set of validation rules for this input element.
 * @return {Boolean} Whether the input value is valid.
*/
function isRequiredConditionMet(value, rules) {
  if (rules.required) {
    if (!value) {
      document.getElementById(rules.msgId).innerHTML = 'This field is ' +
          'required.';
      return false;
    }
    return true;
  }
}


/**
 * Checks that the character length of an input value isn't too long.
 * @param {String} value The value of the input element to check.
 * @param {Array} rules The set of validation rules for this input element.
 * @return {Boolean} Whether the input value length is less than the maximum.
*/
function isLengthValid(value, rules) {
  var maxLength = rules.maxLength;
  if (maxLength) {
    if (value.length > maxLength) {
      document.getElementById(rules.msgId).innerHTML = 'Please ' +
          'enter no more than ' + maxLength + ' characters.';
      return false;
    }
  }
  return true;
}


/**
 * Checks if an input value is within a range.
 * @param {String} value The value of the input element to check.
 * @param {Array} rules The set of validation rules for this input element.
 * @return {Boolean} Whether the input value is within the range.
*/
function isBoundsValid(value, rules) {
  var min = rules.min;
  var max = rules.max;
  if (min && max) {
    if (value > max || value < min) {
      document.getElementById(rules.msgId).innerHTML = 'Please ' +
          'enter a value between ' + min + ' and ' + max;
      return false;
    }
  }
  return true;
}


/**
 * Checks if an input value is formatted correctly.
 * @param {String} value The value of the input element to check.
 * @param {Array} rules The set of validation rules for this input element.
 * @return {Boolean} Whether the input value is valid.
*/
function isContentValid(value, rules) {
  var pattern = rules.test;
  if (pattern) {
    if (!pattern.test(value)) {
      document.getElementById(rules.msgId).innerHTML = rules.testErrorMsg;
      return false;
    }
  }
  return true;
}


/**
 * Validates an input element against a set of rules.
 * @param {Object} value The value to validate.
 * @param {Array} rules The set of rules to use to validate the input.
 * @return {Boolean} Whether the input is validates against the rule.
*/
function validateInput(value, rules) {
  if (isRequiredConditionMet(value, rules) &&
      isLengthValid(value, rules) &&
      isBoundsValid(value, rules) &&
      isContentValid(value, rules)) {

    // Clear the error message
    document.getElementById(rules.msgId).innerHTML = '';
    return true;
  }
  return false;
}


/**
 * Validates a form against a set of rules.
 * @param {Object} form The form to validate.
 * @return {Boolean} Whether the form input is valid.
 */
function validateForm(form) {
  isFormInputValid = true;
  for (inputRule in VALIDATION_RULES) {
    // Check if the form has an input element with an ID that matches a rule.
    formInputElement = form[inputRule];
    if (formInputElement) {
      inputValue = formInputElement.value;
      inputRules = VALIDATION_RULES[inputRule];
      isInputValid = validateInput(inputValue, inputRules);
      if (!isInputValid) {
        isFormInputValid = false;
      }
    }
  }
  return isFormInputValid;
}

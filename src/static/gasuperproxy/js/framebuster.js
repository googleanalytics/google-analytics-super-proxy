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
 * @fileoverview
 * Frame buster code that requires JS to display a page.
 * This framebusting code attempts to protect a page that shouldn't be framed.
 */


(function() {
  try {
    var win = this;
    while (true) {
      if (win.parent == win)
        break;
      eval('win.frameElement.src').substr(0, 1);
      win = win.parent;
    }
    if (win.frameElement != null)throw 'busted';
  } catch (e) {
    document.write('--><plaintext style=display:none><!--');
    if (!open(location, '_top'))
      alert('this content cant be framed');
    top.location = location;
  }
})();

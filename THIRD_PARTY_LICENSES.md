# Third-Party Licenses

This project depends on the following third-party libraries. Their licenses are listed below.

---

## Runtime Dependencies

| Library | Version | License |
|---------|---------|---------|
| [fastapi](https://github.com/fastapi/fastapi) | 0.136.1 | MIT |
| [python-multipart](https://github.com/Kludex/python-multipart) | 0.0.32 | Apache-2.0 |
| [httpx](https://github.com/encode/httpx) | 0.28.1 | BSD-3-Clause |
| [langgraph](https://github.com/langchain-ai/langgraph) | 1.2.1 | MIT |
| [loguru](https://github.com/Delgan/loguru) | 0.7.3 | MIT |
| [pydantic](https://github.com/pydantic/pydantic) | 2.13.4 | MIT |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | 1.2.2 | BSD-3-Clause |
| [tenacity](https://github.com/jd/tenacity) | 9.1.4 | Apache-2.0 |
| [uvicorn](https://github.com/encode/uvicorn) | 0.47.0 | BSD-3-Clause |
| [GitPython](https://github.com/gitpython-developers/GitPython) | 3.1.50 | BSD-3-Clause |
| [tree-sitter](https://github.com/tree-sitter/py-tree-sitter) | 0.25.2 | MIT |
| [tree-sitter-python](https://github.com/tree-sitter/tree-sitter-python) | 0.25.0 | MIT |
| [tree-sitter-typescript](https://github.com/tree-sitter/tree-sitter-typescript) | 0.23.2 | MIT |
| [neo4j](https://github.com/neo4j/neo4j-python-driver) | 6.2.0 | Apache-2.0 |
| [slack-bolt](https://github.com/slackapi/bolt-python) | 1.28.0 | MIT |
| [aiohttp](https://github.com/aio-libs/aiohttp) | 3.14.0 | Apache-2.0 |
| [croniter](https://github.com/kiorky/croniter) | 6.2.2 | MIT |
| [Markdown](https://github.com/Python-Markdown/markdown) | 3.10.2 | BSD-3-Clause |
| [weasyprint](https://github.com/Kozea/WeasyPrint) | 69.0 | BSD-3-Clause |
| [brotli](https://github.com/google/brotli) | 1.2.0 | MIT |
| [cffi](https://github.com/python-cffi/cffi) | 2.0.0 | MIT |
| [cssselect2](https://github.com/Kozea/cssselect2) | 0.9.0 | BSD-3-Clause |
| [fonttools](https://github.com/fonttools/fonttools) | 4.63.0 | MIT |
| [pillow](https://github.com/python-pillow/Pillow) | 12.2.0 | MIT-CMU (HPND) |
| [pycparser](https://github.com/eliben/pycparser) | 3.0 | BSD-3-Clause |
| [pydyf](https://github.com/CourtBouillon/pydyf) | 0.12.1 | BSD-3-Clause |
| [pyphen](https://github.com/Kozea/Pyphen) | 0.17.2 | MPL-1.1 / LGPL-2.1+ / GPL-2.0+ |
| [tinycss2](https://github.com/Kozea/tinycss2) | 1.5.1 | BSD-3-Clause |
| [tinyhtml5](https://github.com/CourtBouillon/tinyhtml5) | 2.1.0 | MIT |
| [webencodings](https://github.com/gsnedders/python-webencodings) | 0.5.1 | BSD-3-Clause |
| [zopfli](https://github.com/nicowillis/zopfli) | 0.4.3 | Apache-2.0 |

## Development Dependencies

| Library | Version | License |
|---------|---------|---------|
| [pytest](https://github.com/pytest-dev/pytest) | 9.0.3 | MIT |
| [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) | 1.4.0 | Apache-2.0 |
| [ruff](https://github.com/astral-sh/ruff) | 0.15.14 | MIT |

---

## License Texts

### MIT License

Used by: fastapi, langgraph, loguru, pydantic, tree-sitter, tree-sitter-python,
tree-sitter-typescript, slack-bolt, croniter, pytest, ruff, aiohttp (partial),
brotli, cffi, fonttools, tinyhtml5

```
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

### Apache License 2.0

Used by: python-multipart, tenacity, neo4j, aiohttp (partial), pytest-asyncio, zopfli

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship made available under
      the License, as indicated by a copyright notice that is included in
      or attached to the work (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and its Derivative Works thereof.

      "Contribution" shall mean, as submitted to the Licensor for inclusion
      in the Work by the copyright owner or by an individual or Legal Entity
      authorized to submit on behalf of the copyright owner. For the purposes
      of this definition, "submitted" means any form of electronic, verbal,
      or written communication sent to the Licensor or its representatives,
      including but not limited to communication on electronic mailing lists,
      source code control systems, and issue tracking systems that are managed
      by, or on behalf of, the Licensor for the purpose of discussing and
      improving the Work, but excluding communication that is conspicuously
      marked or designated in writing by the copyright owner as "Not a
      Contribution."

      "Contributor" shall mean Licensor and any Legal Entity on behalf of
      whom a Contribution has been received by the Licensor and included
      within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by the combined work of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a cross-claim
      or counterclaim in a lawsuit) alleging that the Work or any product
      incorporating the Work constitutes direct or patent infringement, then
      any patent licenses granted to You under this License for that Work
      shall terminate as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or Derivative
          Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, You must include a readable copy of the
          attribution notices contained within such NOTICE file, in
          at least one of the following places: within a NOTICE text
          file distributed as part of the Derivative Works; within
          the Source form or documentation, if provided along with the
          Derivative Works; or, within a display generated by the
          Derivative Works, if and wherever such third-party notices
          normally appear. The contents of the NOTICE file are for
          informational purposes only and do not modify the License.
          You may add Your own attribution notices within Derivative
          Works that You distribute, alongside or as an addendum to
          the NOTICE text from the Work, provided that such additional
          attribution notices cannot be construed as modifying the License.

      You may add Your own license statement for Your modifications and
      may provide additional grant of rights to use, reproduce, modify,
      prepare Derivative Works of, distribute, and sublicense such modifications.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or reproducing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or exemplary damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or all other
      commercial damages or losses), even if such Contributor has been
      advised of the possibility of such damages.

   9. Accepting Warranty or Liability. While redistributing the Work or
      Derivative Works thereof, You may choose to offer, and charge a fee
      for, acceptance of support, warranty, indemnity, or other liability
      obligations and/or rights consistent with this License. However, in
      accepting such obligations, You may offer such obligations only on
      Your own behalf and on Your sole responsibility, not on behalf of
      any other Contributor, and only if You agree to indemnify, defend,
      and hold each Contributor harmless for any liability incurred by,
      or claims asserted against, such Contributor by reason of your
      accepting any warranty or additional liability.

   END OF TERMS AND CONDITIONS
```

---

### BSD 3-Clause License

Used by: httpx, python-dotenv, uvicorn, GitPython, Markdown, weasyprint,
cssselect2, pycparser, pydyf, tinycss2, webencodings

```
Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```

---

### MIT-CMU License (HPND)

Used by: pillow

```
The Python Imaging Library (PIL) is
    Copyright © 1997-2011 by Secret Labs AB
    Copyright © 1995-2011 by Fredrik Lundh and contributors

Pillow is the friendly PIL fork. It is
    Copyright © 2010-2024 by Jeffrey A. Clark (Alex) and contributors

By obtaining, using, and/or copying this software and/or its associated
documentation, you agree that you have read, understood, and will comply
with the following terms and conditions:

Permission to use, copy, modify and distribute this software and its
documentation for any purpose and without fee is hereby granted,
provided that the above copyright notice appears in all copies, and that
both that copyright notice and this permission notice appear in supporting
documentation, and that the name of Secret Labs AB or the author not be
used in advertising or publicity pertaining to distribution of the software
without specific, written prior permission.

SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR BE LIABLE FOR ANY SPECIAL,
INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
```

---

### MPL-1.1 / LGPL-2.1+ / GPL-2.0+ (tri-license)

Used by: pyphen

pyphen is tri-licensed and may be used under any one of the following licences at your option:

- **Mozilla Public License 1.1 (MPL-1.1):** https://www.mozilla.org/en-US/MPL/1.1/
- **GNU Lesser General Public License v2.1 or later (LGPL-2.1+):** https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
- **GNU General Public License v2.0 or later (GPL-2.0+):** https://www.gnu.org/licenses/old-licenses/gpl-2.0.html

Full license texts are available at the URLs above and in the pyphen source distribution at https://github.com/Kozea/Pyphen.

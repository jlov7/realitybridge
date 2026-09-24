# Pinned API excerpt for review

This readable path list accompanies `API-SCHEMA-EXCERPT.json`, captured from `/swagger.v1.json` on the pinned Gitea 1.24.7 image in a new owned loopback run. The historical study did not retain the raw schema.

| Method | Path |
| --- | --- |
| POST | /repos/{owner}/{repo}/issues |
| GET | /repos/{owner}/{repo}/issues/{index} |
| PATCH | /repos/{owner}/{repo}/issues/{index} |
| POST | /repos/{owner}/{repo}/issues/{index}/labels |
| DELETE | /repos/{owner}/{repo}/issues/{index}/labels/{id} |
| POST | /repos/{owner}/{repo}/labels |

The review should challenge whether the declared state and normalization rules preserve every distinction relevant to these operations. Request the live raw swagger before drawing a claim that depends on a field absent from this excerpt.

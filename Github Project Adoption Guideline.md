# Github Project Adoption Guideline and Sample Feature

This is a sample feature to demonstrate how to use [Github project](https://github.com/orgs/sonic-net/projects/8) to track one candidate feature. When you propose one candidate feature for one SONiC community release with this Github project, <br>

Please follow below steps:
 
### How to propose new features?
 
1. For people who have NO edit permission to this project but want to contribute, please follow the “Call for participation” message, e.g Re: Call for participation for SONiC 202305 release (sonicfoundation.dev). <br>
2. For people who can edit github project, if you want to propose a new feature from scratch, please follow below steps: <br>
	- On the "Table View" of project, click Control + Space and provide the Title
	- Click “Enter” button to create a new work item. You can create new item from other views, but steps may be slightly different.
	- fulfill the fields in the ticket (click "Show all fields" to display all fields)
	- Mandatory fields when you submit proposal
	- Title
	- Short Description
	- SAI Header (API) Change Required?
	- Owner Company -- company name who proposed this feature. Please use your personal name if this comes from individual contributor
	- On the left side of the newly created item, click “Convert to issue”
	- Close the issue after the feature is delivered. The issue is used for project tracking purpose, please use HLD PR and code PRs to track the feature design and implementation
3. If the HLD PR already exists, the PR can be added into the release plan by changing the “Projects” field of the PR. Please remember to update the fields info according to the Sample Feature above.	<br>

For new contributors, please [check](https://github.com/sonic-net/SONiC/wiki/Becoming-a-contributor) and pay more attention on section "Pull Request Process".

### How to change the status?
There are two ways to update the status of one proposed feature.

#### Option 1: Drag & drop the feature to different slot on “Board View”
You can drag one feature to another slot to change the status.

![](https://github.com/kannankvs/kvskSONiC/blob/master/assets/img/github_proj_guid_1.png)

#### Option 2: Change the “Status” field on the feature page

![](https://github.com/kannankvs/kvskSONiC/blob/master/assets/img/github_proj_guid_2.png)


### Feature status change flow

1. A new feature proposal will by default go to “Backlog” slot. You can create new feature proposal for future releases in this slot.
2. Once you plan to contribute one specific feature to one specific release, say “SONiC 202305 Release”, you should move that feature to “In Plan Features” slot and leave a comment in the feature PR/Issue by saying “A feature target xxx release”. After this, team should start working on the HLD PR
3. Once the HLD is ready for review by community, the feature should be moved to “HLD Ready for Review” slot and specify an expected “HLD Review Date”. The weekly SONiC community meeting will be used for the HLD review. We will publish the community calendar with Google calendar later, before that, you can pick up a slot which is not booked yet on the project, or ask help from Yanzhao Zhang
4. After the HLD is reviewed in SONiC community, the feature should be moved to “In Progress” slot. Team should update the HLD based on the community feedbacks while working on the code PRs. Code PRs need be added to HLD PR by referring to Pull Request [EVPN VxLAN update for platforms using P2MP tunnel based L2 forwarding #806](https://github.com/sonic-net/SONiC/pull/806)
5. Later, after all code PRs and HLD PR are merged, the feature should be moved to “Done” slot.
6. If one feature need be deferred or withdrawn, the feature should be moved to “Deferred” slot (candidate for next release), or “Backlog” slot (candidate for future releases post next release).
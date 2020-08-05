# Introduction
The scope of this document is to provide the requirements and a high-level design proposal for Sonic dockers management using Kubernetes. 

The existing mode, which we term as '**Legacy mode**' has all container images burned in the image. The systemd manages the features and use docker to start/stop the approprite containers. With this proposal, we extend container images to kubernetes-support, where the image could be downloaded from external repositaries. The external Kubernetes masters could be used to deploy container image updates at a massive scale, through manifests.

# Requirements
The following are the high level requirements to meet.
1. Kubernetes support is optional.
    * Switch could run completely in legacy mode, if desired.
    * Image could be built with no Kubernetes packages, to save image size cost.
    * Current set of commands continue to work as before.
    
2. A feature could be managed using local container image or kubernetes-provided image
    * A feature could be marked for legacy or kubernetes mode, with legacy being default
    * A feature could be switched between two modes.
    * A feature could default to local image, when/where kubernetes image is not available.
    
3. A feature's rules for start/stop stays the same, in either mode (legacy/kubernetes)
    * Set of rules are currently executed through systemd config, start/stop/wait scripts.
    * These rules will stay the same, for both modes
    
4. A feature could be completely kubernetes managed only.
    * The switch image will not have this container image as embedded.
    * The feature is completely controlled by switch as start/stop/enable/disable
    
5. A set of "system service ..." commands will manage the features in both modes.
    * The same set of commands would work transparenly on features, irrespective of their current mode as legacy/kubernetes.
    * This would cover all basic requirements, like start/stop/status/enable/disable/<more as deemed as necessary>
    
6. The monit service would monitor the processes transparently across both modes.



# Non requirements
The following are required, but not addressed in this design doc. This would be addressed in one or more separate docs.

1. The feature deployed by kubernetes must have passed nightly tests.
2. The manifest for the feature must honor controls laid by switch as enable/disable/start/stop.
3. The kube managed container image be built with same base OS & tools docker-layers as switch version.
4. The container image deployed must have cleared standard security checks laid for any SONiC images

    

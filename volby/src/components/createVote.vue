<template>
    <div>
        <div class="card box shadow has-margin-bottom-40">
            <div class="card-content has-padding-bottom-30">
                <template v-if="isLoading">
                    <div class="columns is-centered">
                        <div class="column is-12 has-text-centered">
                            <b-icon pack="fas" icon="sync-alt" size="is-large" custom-class="fa-spin">></b-icon>
                        </div>
                    </div>
                </template>
                <template v-else>
                    <b-field class="title is-1 has-text-centered">
                        <h1 ><strong>{{ this.election.name }}</strong></h1>
                    </b-field>
                    <b-field class="title is-5 has-text-centered">
                        <span>{{ this.election.description }}</span>
                    </b-field>
                    <p class="content title is-6 has-text-centered">
                        <b> Ballot </b>
                    </p>
                    <div class="has-text-centered">
                        <div v-for="(voting_option, index) in this.voting_options_array" :key="index" class="has-margin-bottom-10">
                            <div class="is-divider" v-if="index == voting_options_array.length - 2"></div>
                            <b-field>
                                <b-radio v-model="votingOptionSelected" type="is-sucess" name="name" :native-value="voting_option">
                                    {{ (voting_option.name).toUpperCase() }}
                                </b-radio>
                            </b-field >
                        </div>
                    </div>                    
                    <b-field class="is-pulled-right has-margin-bottom-20">
                        <b-button type="is-success" icon-left="check-circle" rounded @click.prevent="submit()" :loading="isLoadingSubmit">Vote</b-button>
                    </b-field>
                </template>
            </div>
        </div>
    </div>
</template>
<script>
export default{
    data(){
        return{
            title: "Vote",
            electionId: this.$route.params.electionId,
            election: {},
            voting_options_array: [],
            votingOptionSelected: "",
            isLoading: true,
            currentTimestamp: Math.floor(new Date().getTime() / 1000),
            isLoadingSubmit: false
        }
    },
    methods: {
        submit(){
            if(this.votingOptionSelected.name == "NULL" || this.votingOptionSelected.name == "BLANK" ){

                this.$buefy.dialog.confirm({
                    title: 'Default Voting Option Selected',
                    message: 'You just selected a default voting option (<b> NULL / BLANK</b>). If you sure of your vote click <b>Vote</b>',
                    confirmText: 'Vote',
                    type: 'is-warning',
                    hasIcon: true,
                    onConfirm: () => {
                        this.isLoadingSubmit = true
                        axios.post('api/votes/'+ this.votingOptionSelected.voting_option_id, {})
                        .then(response => {
                            this.$router.push("/elections")
                            this.$buefy.toast.open({
                                duration: 3000,
                                message: 'Vote submitted!',
                                type: 'is-success'
                            })
                        })
                        .catch(error => {
                            if(error.response.status == 400) {
                                this.$router.push("/elections")
                                this.$buefy.toast.open({
                                    duration: 3000,
                                    message: "This election doesn't accept votes right now.",
                                    type: 'is-warning'
                                })
                            }
                            console.log(error)
                        })
                        .then(() => {
                            this.isLoadingSubmit = false
                        })
                    }

                })
            }else{
                this.isLoadingSubmit = true
                axios.post('api/votes/'+ this.votingOptionSelected.voting_option_id, {})
                .then(response => {
                    this.$router.push("/elections")
                    this.$buefy.toast.open({
                        duration: 3000,
                        message: 'Vote submitted!',
                        type: 'is-success'
                    })
                })
                .catch(error => {
                    if(error.response.status == 400) {
                        this.$router.push("/elections")
                        this.$buefy.toast.open({
                            duration: 3000,
                            message: "This election doesn't accept votes right now.",
                            type: 'is-warning'
                        })
                    }
                    console.log(error)
                })
                .then(() => {
                    this.isLoadingSubmit = false
                })
            }
        }
    },
    mounted(){

        axios.get('api/elections/'+ this.electionId)
        .then(response => {
            this.election = response.data

            if(!this.election.can_vote){
                this.$router.push("/elections")
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "You don't have permission to access this page.",
                    type: 'is-warning'
                })
                return
            }

            if(this.election.start_timestamp > this.currentTimestamp || this.currentTimestamp > this.election.end_timestamp){
                this.$router.push("/elections")
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "This election doesn't accept votes right now.",
                    type: 'is-warning'
                })
                return
            }

            if(this.election.voted){
                this.$router.push("/elections")
                this.$buefy.toast.open({
                    duration: 3000,
                    message: "You already voted a first time in this election.",
                    type: 'is-warning'
                })
                return
            }

            axios.get('api/elections/'+ this.electionId +'/voting_options')
            .then(response => {
                this.voting_options_array = response.data
                
                let nullOptionIndex = this.voting_options_array.findIndex(v => v.name == "NULL")
                let nullOption = this.voting_options_array.splice(nullOptionIndex,1)[0]

                let blankOptionIndex = this.voting_options_array.findIndex(v => v.name == "BLANK")
                let blankOption = this.voting_options_array.splice(blankOptionIndex,1)[0]

                this.voting_options_array.sort(function(a, b){
                    if(a.id < b.id) { return -1; }
                    if(a.id > b.id) { return 1; }
                    return 0;
                })

                this.voting_options_array.push(nullOption)
                this.voting_options_array.push(blankOption)
            })
            .catch(error => {
                console.log(error)
            })
            .then(() => {
                this.isLoading = false
            })
        })
        .catch(error => {
            console.log(error)
        })


    },
    created() {
        this.$emit('title',this.title)
        this.$emit('back',"/election/" + this.electionId)
    }
}
</script>

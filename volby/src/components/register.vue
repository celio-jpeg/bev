<template>
    <div>
        <div class="section has-padding-top-10">
            <div class="container main">
                <div class="columns is-centered is-full-height is-vcentered">
                    <div class="column has-text-centered has-padding-top-30">
                        <img class="image is-128x128 is-horizontal-center" src="img/icon.png"/>
                        <h1 id="home_title">Volby</h1>
                        <h4 id="home_subtitle">Register</h4>
                        <div class="columns is-centered">
                            <div class="column is-5">
                                <div class="card box shadow has-padding-top-0 has-padding-left-0 has-padding-right-0 has-padding-bottom-0<">
                                    <div class="card-content">
                                        <b-message v-show="isEmailNotUnique" type="is-danger">
                                            The email is already taken. Please, choose another one.
                                        </b-message>
                                        <validation-observer ref="observer" v-slot="{handleSubmit}">
                                            <form @submit.prevent="handleSubmit(submit)">
                                                <validation-provider rules="required|min:2|alpha_spaces" name="Name" v-slot="validationContext">
                                                    <b-field label="Name" :type="getValidationState(validationContext)" :message="validationContext.errors[0]">
                                                        <b-input rounded v-model="name"></b-input>
                                                    </b-field>
                                                </validation-provider>
                                                <validation-provider rules="required|email" name="Email" v-slot="validationContext">
                                                    <b-field label="Email" :type="getValidationState(validationContext)" :message="validationContext.errors[0]">
                                                        <b-input rounded v-model="email"></b-input>
                                                    </b-field>
                                                </validation-provider>
                                                <validation-provider rules="required|capitalLetter|oneNumber|min:6|confirmed:confirmation" name="Password" v-slot="validationContext">
                                                    <b-field label="Password" :type="getValidationState(validationContext)" :message="validationContext.errors[0]">
                                                        <b-input rounded type="password" v-model="password"></b-input>
                                                    </b-field>
                                                </validation-provider>
                                                <validation-provider vid="confirmation" rules="required" v-slot="validationContext">
                                                    <b-field label="Password Confirmation" :type="getValidationState(validationContext)" :message="validationContext.errors[0]">
                                                        <b-input rounded type="password" v-model="confirmation"></b-input>
                                                    </b-field>
                                                </validation-provider>
                                                <b-button class="has-margin-top-20" type="is-primary" expanded rounded native-type="submit" :loading="isLoading" >Register</b-button>
                                            </form>
                                        </validation-observer>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="columns">
                            <div class="column">
                                <b-button type="is-text" tag="router-link" to="/login">Already have an account? Login</b-button>
                            </div>
                        </div>
                        <div class="columns">
                            <div class="column">
                                <b-button type="is-text" tag="router-link" to="/">Home</b-button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <footer class="footer volby-footer has-margin-top-20">
            <div class="columns is-vcentered has-text-centered">
                <div class="column is-3">
                    <img class="image is-horizontal-center" width="50%" src="img/ipleiria.png" />
                </div>
                <div class="column is-6">
                    <p>Copyright © 2020 Bernardo Figueiredo and Célio Mendes @ IPLeiria.</p>
                    <p>All Rights Reserved</p>
                </div>
                <div class="column is-3">
                    <b-button type="is-text" tag="router-link" to="/about" target='_blank'>About Volby</b-button>
                </div>
            </div>
        </footer>
    </div>
</template>
<script>

import { extend } from 'vee-validate';
import { capitalLetter, oneNumber } from 'vee-validate/dist/rules';

extend('oneNumber', {
    validate(value, obj) {
        var count = 0
        count = value.replace(/\D/g, '').length

        if (count == 0) {
            return  'Password at least one number.'
        }else{
            return true;
        }
    }
});

extend('capitalLetter', {
    validate(value, obj) {
        var count=0
        for(var i=0; i<value.length; i++) {
            if(/[A-Z]/.test(value.charAt(i))) count++;
        }

        if (count == 0) {
            return  'Password needs one uppercase letter.'
        }else{
            return true;
        }
    }
});

export default{
    data(){
        return{
            name: "",
            email: "",
            password: "",
            confirmation: "",
            isEmailNotUnique: "",
            isLoading: false
        }
    },
    methods: {
        submit(){
            this.isEmailNotUnique = false
            this.isLoading = true

            axios.post('api/voters',{
                name: this.name,
                voter_id: this.email,
                password: this.password
            })
            .then(response => {
                axios.defaults.headers.common.Authorization = "Bearer " + response.data.accessToken

                this.$store.commit("setAuthToken",response.data.accessToken)
                this.$store.commit("setUser",response.data.user)

                this.$buefy.toast.open({
                    duration: 3000,
                    message: 'Welcome to Volby!',
                    type: 'is-success'
                })
                this.$router.push("/start").catch(e => {})
            })
            .catch(error => {
                if(error.response.status == 409){
                    this.isEmailNotUnique = true
                }
            })
            .then(() => {
                this.isLoading = false
            })
        },
        getValidationState({ dirty, validated, valid = null }) {
            return dirty || validated ? (valid ? "" : "is-danger") : "";
        }
    }
}
</script>

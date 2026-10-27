package org.alex73.belvoice.ttscorpus.model;

import java.util.Objects;

public class WordData {
    private String group;
    private final String words;
    private String phoneticTranscription;
    private String digraph;
    private String trigraph;
    private String diphone;
    private String triphone;
    private String phoneticRule;

    public WordData(String words) {
        this.words = words;
    }

    public WordData(String words, String phoneticTranscription, String diphone, String triphone, String phoneticRule) {
        this(null, words, phoneticTranscription, null, null, diphone, triphone, phoneticRule);
    }

    public WordData(String words, String phoneticTranscription, String digraph, String trigraph, String diphone, String triphone, String phoneticRule) {
        this(null, words, phoneticTranscription, digraph, trigraph, diphone, triphone, phoneticRule);
    }

    public WordData(String group, String words, String phoneticTranscription, String diphone, String triphone, String phoneticRule) {
        this(group, words, phoneticTranscription, null, null, diphone, triphone, phoneticRule);
    }

    public WordData(String group, String words, String phoneticTranscription, String digraph, String trigraph, String diphone, String triphone, String phoneticRule) {
        this.group = group;
        this.words = words;
        this.phoneticTranscription = phoneticTranscription;
        this.digraph = digraph;
        this.trigraph = trigraph;
        this.diphone = diphone;
        this.triphone = triphone;
        this.phoneticRule = phoneticRule;
    }

    public String group() {
        return group;
    }

    public void setGroup(String group) {
        this.group = group;
    }

    public String words() {
        return words;
    }

    public String phoneticTranscription() {
        return phoneticTranscription;
    }

    public void setPhoneticTranscription(String phoneticTranscription) {
        this.phoneticTranscription = phoneticTranscription;
    }

    public String digraph() {
        return digraph;
    }

    public void setDigraph(String digraph) {
        this.digraph = digraph;
    }

    public String trigraph() {
        return trigraph;
    }

    public void setTrigraph(String trigraph) {
        this.trigraph = trigraph;
    }

    public String diphone() {
        return diphone;
    }

    public void setDiphone(String diphone) {
        this.diphone = diphone;
    }

    public String triphone() {
        return triphone;
    }

    public void setTriphone(String triphone) {
        this.triphone = triphone;
    }

    public String phoneticRule() {
        return phoneticRule;
    }

    public void setPhoneticRule(String phoneticRule) {
        this.phoneticRule = phoneticRule;
    }

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        WordData wordData = (WordData) o;
        return Objects.equals(group, wordData.group)
                && Objects.equals(words, wordData.words)
                && Objects.equals(phoneticTranscription, wordData.phoneticTranscription)
                && Objects.equals(digraph, wordData.digraph)
                && Objects.equals(trigraph, wordData.trigraph)
                && Objects.equals(diphone, wordData.diphone)
                && Objects.equals(triphone, wordData.triphone)
                && Objects.equals(phoneticRule, wordData.phoneticRule);
    }

    @Override
    public int hashCode() {
        return Objects.hash(group, words, phoneticTranscription, digraph, trigraph, diphone, triphone, phoneticRule);
    }

    @Override
    public String toString() {
        return "WordData[" +
                "group=" + group + ", " +
                "words=" + words + ", " +
                "phoneticTranscription=" + phoneticTranscription + ", " +
                "digraph=" + digraph + ", " +
                "trigraph=" + trigraph + ", " +
                "diphone=" + diphone + ", " +
                "triphone=" + triphone + ", " +
                "phoneticRule=" + phoneticRule + ']';
    }
}


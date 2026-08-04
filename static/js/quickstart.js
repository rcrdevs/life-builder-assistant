document.addEventListener("DOMContentLoaded", function () {
    var areaRadios = document.querySelectorAll(".js-quickstart-area");
    var goalGroups = document.querySelectorAll(".js-quickstart-goal-group");

    function updateGoalGroups() {
        var selected = document.querySelector(".js-quickstart-area:checked");
        var selectedKey = selected ? selected.value : null;
        goalGroups.forEach(function (group) {
            var isMatch = group.dataset.areaKey === selectedKey;
            group.hidden = !isMatch;
            group.querySelectorAll("input[type=radio]").forEach(function (input) {
                input.disabled = !isMatch;
            });
        });
    }

    areaRadios.forEach(function (radio) {
        radio.addEventListener("change", updateGoalGroups);
    });
    updateGoalGroups();
});

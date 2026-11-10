"use strict";

document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

const bookingForm = document.querySelector("[data-booking-form]");
if (bookingForm) {
  const hotel = bookingForm.querySelector("#hotel_id");
  const room = bookingForm.querySelector("#room_id");
  const rate = bookingForm.querySelector("#nightly_rate");
  const options = Array.from(room.options).map((option) => option.cloneNode(true));
  const updateRooms = () => {
    const selected = room.value;
    room.replaceChildren(...options.filter((option) => !option.dataset.hotel || option.dataset.hotel === hotel.value)
      .map((option) => option.cloneNode(true)));
    if (Array.from(room.options).some((option) => option.value === selected)) room.value = selected;
    rate.required = room.value !== "0";
  };
  hotel.addEventListener("change", updateRooms);
  room.addEventListener("change", () => {
    const selected = room.selectedOptions[0];
    if (selected && selected.dataset.price) rate.value = selected.dataset.price;
    rate.required = room.value !== "0";
  });
  updateRooms();
}

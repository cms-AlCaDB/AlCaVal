// Calcuate time difference in years, months, days, hours, minutes or seconds ago
const timeSince = (date) => {
  console.log(date)
  const seconds = Math.floor((new Date() - date) / 1000);

  var interval = seconds / (60*60*24*365);
  if (interval > 1) return Math.floor(interval) + " years ago";
  interval = seconds / (60*60*24*30);
  if (interval > 1) return Math.floor(interval) + " months ago";
  interval = seconds / (60*60*24);
  if (interval > 1) return Math.floor(interval) + " days ago";
  interval = seconds / (60*60);
  if (interval > 1) return Math.floor(interval) + " hours ago";
  interval = seconds / 60;
  if (interval > 1) return Math.floor(interval) + " minutes ago";
  return Math.floor(seconds) + " seconds ago";
}

export default timeSince;
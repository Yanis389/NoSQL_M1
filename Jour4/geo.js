// B4 — Index géospatial

// Q28. Index 2dsphere
// db.trips.createIndex({ "start station location": "2dsphere" })

var q28 = [
  { $match: { "start station location": { $near: { $geometry: { type: "Point", coordinates: [-73.9855, 40.7580] }, $maxDistance: 500 } } } }
];

// Q29. Remplacement de $near par $geoWithin
// db.trips.countDocuments({ "start station location": { $geoWithin: { $centerSphere: [[-73.9855, 40.7580], 500 / 6378100] } } })

// Q30. Pipeline $geoNear sur stations
// db.stations.createIndex({ "position": "2dsphere" })

var q30 = [
  { $geoNear: {
      near: { type: "Point", coordinates: [-73.9855, 40.7580] },
      distanceField: "distance_metres",
      maxDistance: 1000,
      spherical: true
  } },
  { $project: {
      nom: 1,
      distance_metres: { $round: ["$distance_metres", 0] },
      departs: 1
  } },
  { $sort: { distance_metres: 1 } }
];
